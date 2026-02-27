<script setup lang="ts">
defineProps<{
  show: boolean
  message: string
  type: string
}>()
</script>

<template>
  <Transition name="fade">
    <div v-if="show"
         class="fixed top-4 right-4 z-50 px-5 py-3 rounded-lg shadow-lg text-sm font-medium"
         :class="{
           'bg-green-600 text-white': type === 'success',
           'bg-red-600 text-white': type === 'error',
           'bg-blue-600 text-white': type === 'info',
         }">
      {{ message }}
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
