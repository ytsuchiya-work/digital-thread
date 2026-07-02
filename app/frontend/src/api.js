export async function api(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${path} failed (${res.status}): ${body.slice(0, 300)}`)
  }
  return res.json()
}

export const fmtUsd = (v) =>
  v == null ? '-' : '$' + Math.round(v).toLocaleString('en-US')

export const fmtPct = (v) =>
  v == null ? '-' : (v * 100).toFixed(1) + '%'
