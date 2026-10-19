-- 실무 AI 용어집 · Supabase 스키마 (현재 프로젝트에 적용된 상태의 기록)
-- 새 프로젝트를 만들 때 SQL Editor에서 이 파일 전체를 한 번 실행하면 같은 구조가 된다.
--
-- 위키 트리
--   root ─ category(분야, id 'c.<코드>') ─ topic(주제, id 't.<주제id>') ─ page(문서, id '<용어id>')
--   wiki_nodes.path 예: root/rag/rag-vector/vector-db
--
-- 동기화 흐름
--   저장소 data/*.json → scripts/build.py → supabase/sync-payload.json(커밋)
--   → Supabase에서 select public.wiki_pull();  (GitHub에서 직접 읽어 upsert)
--   삭제는 하지 않는다. 지운 문서는 status='removed'로 표시하고 이력은 남긴다.

-- ───────────── 조회 집계 ─────────────
create table if not exists public.term_hits (
  term_id    text primary key,
  hits       bigint      not null default 0,
  updated_at timestamptz not null default now()
);
alter table public.term_hits enable row level security;
create policy "public read" on public.term_hits for select to anon, authenticated using (true);

create or replace function public.increment_hit(p_term text)
returns void language sql security definer set search_path = public as $$
  update public.term_hits set hits = hits + 1, updated_at = now() where term_id = p_term;
$$;
grant execute on function public.increment_hit(text) to anon, authenticated;

-- ───────────── 위키 트리 ─────────────
create table if not exists public.wiki_nodes (
  id          text primary key,
  parent_id   text references public.wiki_nodes(id) on delete restrict,
  kind        text not null check (kind in ('root','category','topic','page')),
  title_ko    text not null,
  title_en    text,
  description text,
  path        text not null unique,
  depth       smallint not null,
  sort_order  integer not null default 0,
  created_on  date not null default current_date,
  updated_on  date not null default current_date,
  status      text not null default 'active'
);
create index if not exists wiki_nodes_parent_idx on public.wiki_nodes (parent_id, sort_order);

create table if not exists public.wiki_pages (
  node_id   text primary key references public.wiki_nodes(id) on delete cascade,
  abbr      text not null default '',
  level     smallint not null check (level between 1 and 3),
  easy      text not null,
  deep      text not null,
  example   text not null default '',
  revision  integer not null default 1,
  related   text[] not null default '{}'
);

create table if not exists public.wiki_revisions (
  id          bigint generated always as identity primary key,
  node_id     text not null,
  rev_date    date not null,
  change_type text not null check (change_type in ('added','updated','moved','removed')),
  summary     text not null,
  created_at  timestamptz not null default now(),
  unique (rev_date, node_id, change_type)
);
create index if not exists wiki_revisions_date_idx on public.wiki_revisions (rev_date desc);

create table if not exists public.wiki_releases (
  rev_date date primary key,
  title    text not null,
  note     text not null default ''
);

-- 초기 설계에서 만든 링크 테이블(현재는 wiki_pages.related 배열 + wiki_backlinks 뷰를 사용, 비어 있음)
create table if not exists public.wiki_links (
  from_id text not null references public.wiki_nodes(id) on delete cascade,
  to_id   text not null references public.wiki_nodes(id) on delete cascade,
  primary key (from_id, to_id)
);

alter table public.wiki_nodes     enable row level security;
alter table public.wiki_pages     enable row level security;
alter table public.wiki_links     enable row level security;
alter table public.wiki_revisions enable row level security;
alter table public.wiki_releases  enable row level security;
create policy "public read" on public.wiki_nodes     for select to anon, authenticated using (true);
create policy "public read" on public.wiki_pages     for select to anon, authenticated using (true);
create policy "public read" on public.wiki_links     for select to anon, authenticated using (true);
create policy "public read" on public.wiki_revisions for select to anon, authenticated using (true);
create policy "public read" on public.wiki_releases  for select to anon, authenticated using (true);

-- ───────────── 뷰 ─────────────
create or replace view public.wiki_tree with (security_invoker = true) as
with recursive t as (
  select id, parent_id, kind, title_ko, title_en, path, depth, sort_order,
         array[title_ko] as crumbs, array[sort_order] as sort_key
    from public.wiki_nodes where parent_id is null
  union all
  select n.id, n.parent_id, n.kind, n.title_ko, n.title_en, n.path, n.depth, n.sort_order,
         t.crumbs || n.title_ko, t.sort_key || n.sort_order
    from public.wiki_nodes n join t on n.parent_id = t.id
)
select id, parent_id, kind, title_ko, title_en, path, depth, sort_order,
       array_to_string(crumbs[2:], ' > ') as breadcrumb, sort_key
  from t;

create or replace view public.wiki_timeline with (security_invoker = true) as
select rev_date,
       count(*) filter (where change_type = 'added')   as added,
       count(*) filter (where change_type = 'updated') as updated,
       count(*) filter (where change_type = 'moved')   as moved,
       count(*) filter (where change_type = 'removed') as removed,
       jsonb_agg(jsonb_build_object('node_id', node_id, 'type', change_type, 'summary', summary)
                 order by change_type, node_id) as items
  from public.wiki_revisions
 group by rev_date;

create or replace view public.wiki_backlinks with (security_invoker = true) as
select p.node_id as from_id, r.to_id
  from public.wiki_pages p
  cross join lateral unnest(p.related) as r(to_id);

grant select on public.wiki_tree, public.wiki_timeline, public.wiki_backlinks to anon, authenticated;

-- ───────────── 동기화 함수 (관리자 전용) ─────────────
-- wiki_sync(payload): nodes / pages / revisions / releases 를 upsert
-- wiki_pull(ref):     GitHub의 supabase/sync-payload.json을 읽어 wiki_sync 실행
-- 함수 본문은 Supabase 프로젝트에 적용된 버전과 같다. (Database > Functions에서 확인)
create extension if not exists http with schema extensions;
