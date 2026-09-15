import { onUnmounted, ref } from 'vue'
import { api } from '../api'
import { describeError } from '../errorMessages'

const POLL_INTERVAL_MS = 2000

/**
 * Запуск парсинга и слежение за ходом прогона.
 *
 * Парсинг идёт в очереди и занимает минуты, поэтому HTTP-ответ на отправку
 * формы означает лишь «задача принята». Реальный результат приходит опросом
 * статуса прогона, пока он не станет терминальным.
 */
export function useParseRun() {
  const run = ref(null)
  const submitting = ref(false)
  const error = ref(null)
  const fieldErrors = ref({})

  let timer = null

  function stopPolling() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  onUnmounted(stopPolling)

  async function poll(onFinished) {
    try {
      const data = await api.get(`/api/parse-runs/${run.value.id}`)
      run.value = data.data

      if (run.value.status === 'success' || run.value.status === 'failed') {
        stopPolling()
        if (run.value.status === 'failed') {
          error.value = describeError(run.value.error_code, run.value.error_message)
        }
        onFinished?.(run.value)
        return
      }
      timer = setTimeout(() => poll(onFinished), POLL_INTERVAL_MS)
    } catch (err) {
      stopPolling()
      error.value = err.message
    }
  }

  async function start(url, onFinished) {
    stopPolling()
    submitting.value = true
    error.value = null
    fieldErrors.value = {}
    run.value = null

    try {
      const data = await api.post('/api/organizations', { url })
      run.value = data.parse_run.data ?? data.parse_run
      timer = setTimeout(() => poll(onFinished), POLL_INTERVAL_MS)
      return true
    } catch (err) {
      fieldErrors.value = err.errors || {}
      error.value = Object.values(err.errors || {}).flat()[0] || err.message
      return false
    } finally {
      submitting.value = false
    }
  }

  const isRunning = () =>
    run.value !== null && ['pending', 'running'].includes(run.value.status)

  return { run, submitting, error, fieldErrors, start, isRunning, stopPolling }
}
