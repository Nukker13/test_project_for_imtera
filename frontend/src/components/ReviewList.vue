<script setup>
import { computed } from 'vue'

const props = defineProps({
  reviews: { type: Array, required: true },
  meta: { type: Object, default: null },
})

const emit = defineEmits(['page'])

const currentPage = computed(() => props.meta?.current_page ?? 1)
const lastPage = computed(() => props.meta?.last_page ?? 1)

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru-RU', { dateStyle: 'long' })
}
</script>

<template>
  <section class="card">
    <header class="reviews-header">
      <h2 class="card__title">Отзывы</h2>
      <span v-if="meta" class="muted">
        Страница {{ currentPage }} из {{ lastPage }} · всего {{ meta.total }}
      </span>
    </header>

    <p v-if="!reviews.length" class="muted">Отзывов пока нет.</p>

    <ul v-else class="reviews">
      <li v-for="review in reviews" :key="review.id" class="review">
        <div class="review__head">
          <span class="review__author">{{ review.author_name }}</span>
          <span class="review__rating" :aria-label="`Оценка ${review.rating} из 5`">
            {{ '★'.repeat(review.rating) }}<span class="review__rating-dim">{{ '★'.repeat(5 - review.rating) }}</span>
          </span>
          <time class="muted">{{ formatDate(review.reviewed_at) }}</time>
        </div>
        <p v-if="review.text" class="review__text">{{ review.text }}</p>
        <p v-else class="muted review__text">Без текста — только оценка.</p>
      </li>
    </ul>

    <nav v-if="lastPage > 1" class="pager">
      <button
        class="btn btn--ghost"
        type="button"
        :disabled="currentPage <= 1"
        @click="emit('page', currentPage - 1)"
      >
        Назад
      </button>
      <span class="muted">{{ currentPage }} / {{ lastPage }}</span>
      <button
        class="btn btn--ghost"
        type="button"
        :disabled="currentPage >= lastPage"
        @click="emit('page', currentPage + 1)"
      >
        Вперёд
      </button>
    </nav>
  </section>
</template>
