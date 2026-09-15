import { ref } from 'vue'
import { api } from '../api'

// Состояние пользователя общее на всё приложение, поэтому ref-ы объявлены вне
// функции: composable здесь работает как маленький синглтон-стор.
const user = ref(null)
const checked = ref(false)

export function useAuth() {
  const loading = ref(false)
  const error = ref(null)
  const fieldErrors = ref({})

  /** Восстановление сессии при загрузке страницы (кука могла остаться). */
  async function fetchUser() {
    try {
      const data = await api.get('/api/user')
      user.value = data.user
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  async function login(email, password) {
    loading.value = true
    error.value = null
    fieldErrors.value = {}
    try {
      const data = await api.post('/api/login', { email, password })
      user.value = data.user
      return true
    } catch (err) {
      fieldErrors.value = err.errors || {}
      error.value = Object.values(err.errors || {}).flat()[0] || err.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await api.post('/api/logout')
    } finally {
      user.value = null
    }
  }

  return { user, checked, loading, error, fieldErrors, fetchUser, login, logout }
}
