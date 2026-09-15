<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const email = ref('')
const password = ref('')
const { login, loading, error, fieldErrors } = useAuth()
const router = useRouter()

async function submit() {
  if (await login(email.value, password.value)) {
    router.replace({ name: 'dashboard' })
  }
}
</script>

<template>
  <div class="login">
    <form class="card login__form" @submit.prevent="submit">
      <h1 class="login__title">Вход</h1>

      <label class="field">
        <span class="field__label">Email</span>
        <input
          v-model="email"
          class="field__input"
          type="email"
          autocomplete="username"
          required
          :disabled="loading"
        />
        <span v-if="fieldErrors.email" class="field__error">{{ fieldErrors.email[0] }}</span>
      </label>

      <label class="field">
        <span class="field__label">Пароль</span>
        <input
          v-model="password"
          class="field__input"
          type="password"
          autocomplete="current-password"
          required
          :disabled="loading"
        />
        <span v-if="fieldErrors.password" class="field__error">{{ fieldErrors.password[0] }}</span>
      </label>

      <p v-if="error && !fieldErrors.email" class="alert alert--error">{{ error }}</p>

      <button class="btn btn--primary" type="submit" :disabled="loading">
        {{ loading ? 'Входим…' : 'Войти' }}
      </button>
    </form>
  </div>
</template>
