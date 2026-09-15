<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useParseRun } from '../composables/useParseRun'
import { useReviews } from '../composables/useReviews'
import OrganizationStats from '../components/OrganizationStats.vue'
import ReviewList from '../components/ReviewList.vue'
import ParseProgress from '../components/ParseProgress.vue'

const url = ref('')
const organizations = ref([])
const selectedId = ref(null)

const { run, submitting, error: runError, fieldErrors, start, isRunning } = useParseRun()
const { organization, reviews, meta, loading, error: reviewsError, load, loadReviews } = useReviews()

onMounted(loadOrganizations)

async function loadOrganizations() {
  const data = await api.get('/api/organizations')
  organizations.value = data.data
}

async function submit() {
  await start(url.value, async (finished) => {
    if (finished.status === 'success' && finished.organization_id) {
      await loadOrganizations()
      await select(finished.organization_id)
    }
  })
}

async function select(id) {
  selectedId.value = id
  await load(id, 1)
}

function changePage(page) {
  loadReviews(selectedId.value, page)
}
</script>

<template>
  <div class="dashboard">
    <section class="card">
      <h2 class="card__title">Настройки организации</h2>
      <p class="muted">
        Укажите ссылку на карточку организации в Яндекс.Картах — короткая ссылка тоже подойдёт.
      </p>

      <form class="settings-form" @submit.prevent="submit">
        <input
          v-model="url"
          class="field__input"
          type="url"
          placeholder="https://yandex.ru/maps/org/…"
          required
          :disabled="submitting || isRunning()"
        />
        <button class="btn btn--primary" type="submit" :disabled="submitting || isRunning()">
          {{ submitting || isRunning() ? 'Собираем…' : 'Собрать отзывы' }}
        </button>
      </form>

      <span v-if="fieldErrors.url" class="field__error">{{ fieldErrors.url[0] }}</span>

      <ParseProgress v-if="run" :run="run" :error="runError" />
    </section>

    <section v-if="organizations.length" class="card">
      <h2 class="card__title">Разобранные организации</h2>
      <ul class="org-list">
        <li v-for="org in organizations" :key="org.id">
          <button
            class="org-list__item"
            :class="{ 'org-list__item--active': org.id === selectedId }"
            type="button"
            @click="select(org.id)"
          >
            <span class="org-list__name">{{ org.name || org.url }}</span>
            <span class="muted">{{ org.stored_reviews_count }} отзывов в базе</span>
          </button>
        </li>
      </ul>
    </section>

    <p v-if="loading" class="muted">Загружаем отзывы…</p>
    <p v-else-if="reviewsError" class="alert alert--error">{{ reviewsError }}</p>

    <template v-else-if="organization">
      <OrganizationStats :organization="organization" />
      <ReviewList :reviews="reviews" :meta="meta" @page="changePage" />
    </template>
  </div>
</template>
