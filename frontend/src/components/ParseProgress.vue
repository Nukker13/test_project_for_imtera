<script setup>
import { computed } from 'vue'
import { describeFallback } from '../errorMessages'

const props = defineProps({
  run: { type: Object, required: true },
  error: { type: String, default: null },
})

const isActive = computed(() => ['pending', 'running'].includes(props.run.status))
const isFailed = computed(() => props.run.status === 'failed')
const isSuccess = computed(() => props.run.status === 'success')
</script>

<template>
  <div class="progress">
    <div v-if="isActive" class="alert alert--info">
      <span class="spinner" aria-hidden="true"></span>
      <span v-if="run.status === 'pending'">Задача в очереди…</span>
      <span v-else>
        Собираем отзывы
        <template v-if="run.pages_fetched">— страниц обработано: {{ run.pages_fetched }}</template>
      </span>
    </div>

    <div v-else-if="isFailed" class="alert alert--error">
      <strong>Не удалось собрать отзывы.</strong>
      <span>{{ error || run.error_message }}</span>
      <!-- Код ошибки оставлен на виду специально: по нему однозначно понятно,
           что именно сломалось, без чтения логов контейнера. -->
      <code v-if="run.error_code" class="alert__code">{{ run.error_code }}</code>
    </div>

    <div v-else-if="isSuccess" class="alert alert--success">
      <span>Готово: собрано {{ run.reviews_fetched }} отзывов за {{ run.pages_fetched }} стр.</span>
      <span v-if="run.degraded" class="badge badge--warn">
        {{ describeFallback(run.fallback_reason) }}
      </span>
    </div>
  </div>
</template>
