/** Demo build flag: GitHub Pages has no FastAPI/MySQL, so /api is served from snapshots. */
export const isDemo = import.meta.env.VITE_DEMO === '1'
