/** Static demo backend: serves the GitHub Pages build from JSON snapshots. */
const BASE = import.meta.env.BASE_URL
const cache = new Map<string, Promise<any>>()

function load(name: string): Promise<any> {
  if (!cache.has(name)) {
    cache.set(name, fetch(`${BASE}demo/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`demo snapshot ${name} missing`)
      return r.json()
    }))
  }
  return cache.get(name)!
}

function json(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {status, headers: {'Content-Type': 'application/json; charset=utf-8'}})
}

const PERIOD_GROUPS = ['战国', '秦', '西汉', '东汉', '汉', '三国', '东晋', '西晋', '晋', '十六国', '南北朝', '隋', '唐', '五代', '辽', '北宋', '南宋', '宋', '西夏', '金', '元', '明', '清', '民国', '近现代']

function periodGroup(row: any): string {
  if (row.period_conflict) return '分期待核对'
  const value = String(row.period || '')
  for (const group of PERIOD_GROUPS) if (value.startsWith(group)) return group
  return '未归类'
}

function catalogue(data: any, params: URLSearchParams) {
  const q = (params.get('q') || '').trim()
  const institution = params.get('institution') || ''
  const period = params.get('period') || ''
  const character = params.get('character') || ''
  const page = Math.max(1, Number(params.get('page') || 1))
  const pageSize = Math.min(48, Math.max(1, Number(params.get('page_size') || 12)))
  const all = data.items as any[]
  const rows = all.filter((r) => (!institution || r.museum === institution)
    && (!period || periodGroup(r) === period)
    && (!character || String(r.transcription || '').includes(character))
    && (!q || [r.official_title, r.transcription, r.accession_number, r.catalogue_record_id, r.period, r.material, r.maker].join(' ').includes(q)))
  const start = (page - 1) * pageSize
  return {items: rows.slice(start, start + pageSize), matched: rows.length, total_published: all.length, page, page_size: pageSize, notice: '静态演示：数量表示已接入的官方条目，不是馆藏总件数；组印按一条记录计。'}
}

function graph(data: any, params: URLSearchParams) {
  const q = (params.get('q') || '').trim()
  const kind = params.get('kind') || ''
  const status = params.get('status') || ''
  const focus = params.get('focus') || ''
  const depth = Math.min(2, Math.max(0, Number(params.get('depth') || 1)))
  const anyFilter = q || kind || status || focus
  if (!anyFilter) return data
  let nodes = (data.nodes as any[]).filter((n) => (!q || String(n.label).includes(q)) && (!kind || n.kind === kind) && (!status || (n.statuses || []).includes(status)))
  if (focus) {
    const keep = new Set<string>([focus])
    let frontier = [focus]
    for (let step = 0; step < depth; step += 1) {
      const next: string[] = []
      for (const e of data.edges as any[]) {
        if (frontier.includes(e.source) && !keep.has(e.target)) { keep.add(e.target); next.push(e.target) }
        if (frontier.includes(e.target) && !keep.has(e.source)) { keep.add(e.source); next.push(e.source) }
      }
      frontier = next
    }
    nodes = nodes.filter((n) => keep.has(n.id))
  }
  const ids = new Set(nodes.map((n) => n.id))
  const edges = (data.edges as any[]).filter((e) => ids.has(e.source) && ids.has(e.target))
  const docIds = new Set(edges.map((e) => e.document_id))
  return {
    ...data,
    nodes,
    edges,
    documents: (data.documents as any[]).filter((d) => docIds.has(d.id)),
    counts: {...data.counts, nodes: nodes.length, edges: edges.length, documents: docIds.size, matched: nodes.length, context: focus ? Math.max(0, nodes.length - 1) : 0},
  }
}

function findPath(data: any, params: URLSearchParams) {
  const start = params.get('start') || ''
  const end = params.get('end') || ''
  const nodes = new Map<string, any>((data.nodes as any[]).map((n) => [n.id, n]))
  if (!nodes.has(start) || !nodes.has(end)) return json({detail: '路径端点不存在或被筛选排除'}, 404)
  const adjacency = new Map<string, Array<[string, any]>>()
  for (const id of nodes.keys()) adjacency.set(id, [])
  for (const e of data.edges as any[]) {
    adjacency.get(e.source)?.push([e.target, e])
    adjacency.get(e.target)?.push([e.source, e])
  }
  const queue = [start]
  const previous = new Map<string, [string, any] | null>([[start, null]])
  while (queue.length) {
    const item = queue.shift()!
    if (item === end) break
    for (const [other, edge] of adjacency.get(item) || []) {
      if (!previous.has(other)) { previous.set(other, [item, edge]); queue.push(other) }
    }
  }
  if (!previous.has(end)) return json({found: false, nodes: [], edges: [], documents: [], notice: '当前有据关系中没有路径。'})
  const ids = [end]
  const edges: any[] = []
  let cursor = end
  while (previous.get(cursor)) {
    const [next, edge] = previous.get(cursor)!
    cursor = next
    ids.push(cursor)
    edges.push(edge)
  }
  edges.reverse(); ids.reverse()
  const docIds = new Set(edges.map((e) => e.document_id))
  return json({found: true, nodes: ids.map((id) => nodes.get(id)), edges, documents: (data.documents as any[]).filter((d) => docIds.has(d.id)), notice: '无向最短资料关联路径；共享书体或汉字不构成传承关系。'})
}

function knowledge(rows: any[], params: URLSearchParams) {
  const q = (params.get('q') || '').trim()
  const category = params.get('category') || ''
  return rows.filter((r) => (!category || r.category === category)
    && (!q || [r.title, r.content, r.category, r.source_title].join(' ').includes(q)))
}

async function handle(url: URL, method: string): Promise<Response> {
  const path = url.pathname.replace(/^\/api/, '')
  if (method !== 'GET') return json({detail: '静态演示站不提供写入功能；上传、修复、STL 与制作记录需在本机运行完整系统。'}, 503)
  if (path === '/health') {
    const seals = await load('seals')
    const artifacts = (seals as any[]).reduce((sum, s) => sum + (s.artifacts || []).length, 0)
    return json({database: 'connected', database_engine: '静态快照', ai: {torch_installed: false, restoration: {configured: false, state: 'unavailable', reason: '静态演示未包含模型推理'}, recognition: {configured: false, state: 'unavailable', reason: '静态演示未包含模型推理'}, culture: {configured: false, state: 'unavailable'}}, counts: {seals: (seals as any[]).length, artifacts}})
  }
  if (path === '/heritage/overview') return json(await load('overview'))
  if (path === '/heritage/catalogue') return json(catalogue(await load('catalogue'), url.searchParams))
  if (path === '/heritage/bibliography') return json((await load('overview')).bibliography)
  if (path === '/graph') return json(graph(await load('graph'), url.searchParams))
  if (path === '/graph/path') return findPath(await load('graph'), url.searchParams)
  if (path === '/knowledge') return json(knowledge(await load('knowledge'), url.searchParams))
  if (path === '/studio/state') return json(await load('studio-state'))
  if (path === '/studio/catalog') return json(await load('studio-catalog'))
  if (path === '/seals') return json(await load('seals'))
  if (path.startsWith('/seals/')) {
    const seals = await load('seals')
    const hit = (seals as any[]).find((s) => path === `/seals/${s.id}`)
    return hit ? json(hit) : json({detail: '演示快照中没有这条记录'}, 404)
  }
  if (path === '/events') return json(await load('events'))
  return json({detail: `静态演示未包含接口 ${path}`}, 404)
}

export function installStaticApi() {
  const realFetch = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const url = new URL(raw, location.href)
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return realFetch(input as RequestInfo, init)
    const method = (init?.method || (typeof input === 'object' && 'method' in input ? input.method : 'GET')).toUpperCase()
    return handle(url, method).catch((e) => json({detail: e instanceof Error ? e.message : '快照读取失败'}, 500))
  }
}
