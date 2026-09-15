<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const { user, checked, fetchUser, logout } = useAuth()
const router = useRouter()
const route = useRoute()

// Сессия проверяется один раз при старте: кука могла остаться от прошлого
// визита, и в этом случае логин показывать не нужно.
onMounted(fetchUser)

watch([checked, user, () => route.name], ([isChecked, currentUser, name]) => {
  if (!isChecked) return
  if (!currentUser && name !== 'login') router.replace({ name: 'login' })
  if (currentUser && name === 'login') router.replace({ name: 'dashboard' })
})

async function handleLogout() {
  await logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <div class="app">
    <header v-if="user" class="app__header">
      <div class="app__brand">Отзывы из Яндекс.Карт</div>
      <div class="app__user">
        <span>{{ user.email }}</span>
        <button class="btn btn--ghost" type="button" @click="handleLogout">Выйти</button>
      </div>
    </header>

    <main class="app__main">
      <p v-if="!checked" class="muted">Проверяем сессию…</p>
      <RouterView v-else />
    </main>
  </div>
</template>
