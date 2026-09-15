/**
 * Тонкая обёртка над fetch для общения с Laravel.
 *
 * Две вещи, без которых Sanctum в SPA-режиме не работает:
 *  - credentials: 'include' — иначе сессионная кука не уедет с запросом;
 *  - заголовок X-XSRF-TOKEN на все небезопасные методы, значение берётся из
 *    куки XSRF-TOKEN, которую выдаёт /sanctum/csrf-cookie.
 */

class ApiError extends Error {
  constructor(message, { status, errors = {}, code = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
    this.code = code
  }
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : null
}

/** CSRF-куку достаточно получить один раз за сессию страницы. */
let csrfReady = null

async function ensureCsrfCookie() {
  if (!csrfReady) {
    csrfReady = fetch('/sanctum/csrf-cookie', { credentials: 'include' })
  }
  await csrfReady
}

async function request(method, url, body) {
  const options = {
    method,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
  }

  if (method !== 'GET') {
    await ensureCsrfCookie()
    const token = readCookie('XSRF-TOKEN')
    if (token) options.headers['X-XSRF-TOKEN'] = token
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json'
      options.body = JSON.stringify(body)
    }
  }

  const response = await fetch(url, options)

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    throw new ApiError(payload?.message || `Ошибка запроса (${response.status})`, {
      status: response.status,
      errors: payload?.errors || {},
      code: payload?.error_code || null,
    })
  }

  return payload
}

export const api = {
  get: (url) => request('GET', url),
  post: (url, body) => request('POST', url, body),
}

export { ApiError }
