<template>
  <div class="app-container">
    <NuxtRouteAnnouncer />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<style>
.app-container {
  min-height: 100vh;
  background-color: var(--bg-dark);
}
</style>
