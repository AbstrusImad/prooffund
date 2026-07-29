import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import DashboardView from "./views/DashboardView.vue";
import ProjectView from "./views/ProjectView.vue";
import CreateView from "./views/CreateView.vue";
import ProfileView from "./views/ProfileView.vue";
import GovernanceView from "./views/GovernanceView.vue";
import "./style.css";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", name: "dashboard", component: DashboardView },
    { path: "/projects/new", name: "create", component: CreateView },
    { path: "/projects/:id", name: "project", component: ProjectView },
    { path: "/profile", name: "profile", component: ProfileView },
    { path: "/governance", name: "governance", component: GovernanceView },
  ],
});

createApp(App).use(router).mount("#app");
