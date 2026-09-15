import { ref } from 'vue'
import { api } from '../api'

/** Организация и её отзывы постранично (по 50, как задано в ТЗ). */
export function useReviews() {
  const organization = ref(null)
  const reviews = ref([])
  const meta = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function loadOrganization(id) {
    const data = await api.get(`/api/organizations/${id}`)
    organization.value = data.data
  }

  async function loadReviews(id, page = 1) {
    loading.value = true
    error.value = null
    try {
      const data = await api.get(`/api/organizations/${id}/reviews?page=${page}`)
      reviews.value = data.data
      meta.value = data.meta
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function load(id, page = 1) {
    loading.value = true
    error.value = null
    try {
      await loadOrganization(id)
      await loadReviews(id, page)
    } catch (err) {
      error.value = err.message
      loading.value = false
    }
  }

  return { organization, reviews, meta, loading, error, load, loadReviews }
}
