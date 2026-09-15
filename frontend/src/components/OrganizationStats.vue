<script setup>
const props = defineProps({
  organization: { type: Object, required: true },
})

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' })
}
</script>

<template>
  <section class="card">
    <header class="org-header">
      <h2 class="card__title">{{ organization.name || 'Организация' }}</h2>
      <a class="muted" :href="organization.url" target="_blank" rel="noopener">Карточка в Яндекс.Картах</a>
    </header>
    <p v-if="organization.address" class="muted">{{ organization.address }}</p>

    <!-- Количество оценок и количество отзывов показываются раздельно и точными
         числами — это отдельное требование ТЗ. Оценку ставят молча, отзыв пишут
         текстом, поэтому числа почти всегда расходятся. -->
    <dl class="stats">
      <div class="stats__item">
        <dt class="stats__label">Средний рейтинг</dt>
        <dd class="stats__value stats__value--accent">
          {{ organization.rating_avg ?? '—' }}
        </dd>
      </div>
      <div class="stats__item">
        <dt class="stats__label">Оценок</dt>
        <dd class="stats__value">{{ organization.ratings_count ?? '—' }}</dd>
      </div>
      <div class="stats__item">
        <dt class="stats__label">Отзывов</dt>
        <dd class="stats__value">{{ organization.reviews_count ?? '—' }}</dd>
      </div>
      <div class="stats__item">
        <dt class="stats__label">Собрано в базу</dt>
        <dd class="stats__value">{{ organization.stored_reviews_count ?? '—' }}</dd>
      </div>
    </dl>

    <p class="muted">Последний сбор: {{ formatDate(organization.last_parsed_at) }}</p>
  </section>
</template>
