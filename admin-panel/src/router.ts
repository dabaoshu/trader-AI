import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/records',
    },
    {
      path: '/records',
      name: 'Records',
      component: () => import('./views/RecordsView.vue'),
    },
    {
      path: '/screener',
      name: 'Screener',
      component: () => import('./views/ScreenerView.vue'),
    },
  ],
})

export default router
