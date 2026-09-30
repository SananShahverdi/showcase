// A portfolio build mounts this complete application beneath its project route.
const slug = import.meta.env.BASE_URL.match(/^\/demos\/([^/]+)\//)?.[1]
export const projectRoot = slug ? `/api/projects/${slug}` : ''

export function apiBase(standaloneBase: string): string {
  return projectRoot ? `${projectRoot}/api` : standaloneBase.replace(/\/$/, '')
}

export function errorMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (!item || typeof item !== 'object' || !('msg' in item) || typeof item.msg !== 'string') return []
      const field = 'loc' in item && Array.isArray(item.loc) ? item.loc.slice(1).join('.') : ''
      return [field ? `${field}: ${item.msg}` : item.msg]
    })
    if (messages.length) return messages.join('; ')
  }
  return `Request failed (${status})`
}

if (projectRoot && !document.getElementById('portfolio-back-link')) {
  const link = document.createElement('a')
  link.id = 'portfolio-back-link'
  link.href = '/'
  link.textContent = '← Portfolio'
  link.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:1000;display:inline-flex;align-items:center;min-height:44px;padding:0 18px;border:1px solid #516962;border-radius:999px;background:#14251f;color:#f1f7f4;font:600 13px system-ui,sans-serif;text-decoration:none;box-shadow:0 4px 20px #0003;outline-offset:4px;'
  document.body.append(link)
}
