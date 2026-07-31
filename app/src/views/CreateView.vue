<script setup>
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft, ArrowRight, Check, Image, Link2, Rocket } from "lucide-vue-next";
import { useProofFund } from "../stores/proofFund";
import { toWei } from "../services/genlayer";

const router = useRouter();
const { state, isConnected, connect, transact } = useProofFund();
const submitting = ref(false);
const formError = ref("");
const form = reactive({
  title: "",
  category: "Open source",
  summary: "",
  description: "",
  website: "",
  image: "",
  goal: "10",
  deadline: "",
  trancheTitle: "Discovery and public specification",
  trancheGoal: "4",
  trancheDeadline: "",
});

const validationIssue = computed(() => {
  if (form.title.trim().length < 4) return "Project name must contain at least 4 characters.";
  if (form.summary.trim().length < 20) return "One-line outcome must contain at least 20 characters.";
  if (form.description.trim().length < 80) return "Full description must contain at least 80 characters.";
  if (!/^https:\/\/.+/i.test(form.website.trim())) return "Project URL must begin with https://.";
  if (form.image && !/^https:\/\/.+/i.test(form.image.trim())) return "Cover image URL must begin with https://.";
  try {
    if (toWei(form.goal) <= 0n) return "Funding goal must be greater than zero.";
    if (form.trancheTitle.trim().length < 4) return "Initial tranche title must contain at least 4 characters.";
    const trancheGoal = toWei(form.trancheGoal);
    if (trancheGoal <= 0n) return "Initial tranche goal must be greater than zero.";
    if (trancheGoal > toWei(form.goal)) return "Initial tranche cannot exceed the project goal.";
  } catch (error) {
    return error.message;
  }
  if (!form.deadline) return "Choose a funding deadline.";
  if (new Date(form.deadline).getTime() <= Date.now()) return "Funding deadline must be in the future.";
  if (!form.trancheDeadline) return "Choose an initial tranche deadline.";
  if (new Date(form.trancheDeadline).getTime() <= Date.now()) return "Initial tranche deadline must be in the future.";
  if (new Date(form.trancheDeadline).getTime() > new Date(form.deadline).getTime()) return "Initial tranche must close on or before the project deadline.";
  return "";
});
const ready = computed(() => !validationIssue.value);

const submit = async () => {
  formError.value = "";
  if (!ready.value) {
    formError.value = validationIssue.value;
    return;
  }
  if (!isConnected.value) {
    await connect();
  }
  if (!state.wallet) return;
  submitting.value = true;
  try {
    await transact(
      "Creating project",
      "create_project",
      [
        form.title,
        form.category,
        form.summary,
        form.description,
        form.website,
        form.image,
        toWei(form.goal),
        Math.floor(new Date(form.deadline).getTime() / 1000),
        form.trancheTitle,
        toWei(form.trancheGoal),
        Math.floor(new Date(form.trancheDeadline).getTime() / 1000),
      ],
      0n,
      { successMessage: "Project created and published to the Bradbury registry." },
    );
    const own = state.projects
      .filter(
        (project) =>
          project.creator?.toLowerCase() === state.wallet.toLowerCase() &&
          project.title === form.title,
      )
      .at(-1);
    router.push(own ? `/projects/${own.id}` : "/");
  } catch (error) {
    formError.value = error?.message || "Project creation failed.";
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <div class="page narrow-page">
    <RouterLink class="back-link" to="/"><ArrowLeft :size="16" /> Back to registry</RouterLink>
    <header class="form-heading">
      <span class="eyebrow"><Rocket :size="15" /> New funding agreement</span>
      <h1>Define the work before asking for trust.</h1>
      <p>Create the public project record. Milestones are added from its workspace.</p>
    </header>

    <form class="project-form" @submit.prevent="submit">
      <section class="form-section">
        <div class="section-number">01</div>
        <div class="form-section-body">
          <h2>Project identity</h2>
          <p>Clear enough to scan, specific enough to evaluate.</p>
          <div class="field-grid">
            <label class="field span-2">
              <span>Project name</span>
              <input v-model.trim="form.title" maxlength="80" required placeholder="e.g. Public Data Observatory" />
              <small>{{ form.title.length }}/80</small>
            </label>
            <label class="field">
              <span>Category</span>
              <select v-model="form.category">
                <option>Open source</option>
                <option>Public goods</option>
                <option>Research</option>
                <option>Climate</option>
                <option>Creator economy</option>
                <option>Infrastructure</option>
              </select>
            </label>
            <label class="field">
              <span>Funding goal</span>
              <div class="input-suffix"><input v-model="form.goal" inputmode="decimal" required /><b>GEN</b></div>
            </label>
            <label class="field span-2">
              <span>One-line outcome</span>
              <textarea v-model.trim="form.summary" maxlength="180" required rows="2" placeholder="What becomes true if this project succeeds?"></textarea>
              <small>{{ form.summary.length }}/180</small>
            </label>
          </div>
        </div>
      </section>

      <section class="form-section">
        <div class="section-number">02</div>
        <div class="form-section-body">
          <h2>Initial funding tranche</h2>
          <p>Open the first bounded capital commitment. Additional tranches can be added from the project workspace.</p>
          <div class="field-grid">
            <label class="field">
              <span>Tranche title</span>
              <input v-model.trim="form.trancheTitle" maxlength="100" required />
            </label>
            <label class="field">
              <span>Tranche target</span>
              <div class="input-suffix"><input v-model="form.trancheGoal" inputmode="decimal" required /><b>GEN</b></div>
            </label>
            <label class="field">
              <span>Tranche deadline</span>
              <input v-model="form.trancheDeadline" type="date" required />
            </label>
          </div>
        </div>
      </section>

      <section class="form-section">
        <div class="section-number">03</div>
        <div class="form-section-body">
          <h2>Public context</h2>
          <p>This becomes the durable context validators and backers can inspect.</p>
          <div class="field-grid">
            <label class="field span-2">
              <span>Full description</span>
              <textarea v-model.trim="form.description" maxlength="3000" required rows="8" placeholder="Describe the problem, users, approach, risks, and intended public outcome."></textarea>
              <small>{{ form.description.length }}/3000 · minimum 80</small>
            </label>
            <label class="field">
              <span><Link2 :size="15" /> Project URL</span>
              <input v-model.trim="form.website" type="url" required placeholder="https://..." />
            </label>
            <label class="field">
              <span><Image :size="15" /> Cover image URL</span>
              <input v-model.trim="form.image" type="url" placeholder="https://..." />
            </label>
            <label class="field">
              <span>Funding deadline</span>
              <input v-model="form.deadline" type="date" required />
            </label>
          </div>
        </div>
      </section>

      <footer class="form-submit">
        <div>
          <Check :size="17" />
          <span v-if="formError" class="form-error">{{ formError }}</span>
          <span v-else-if="!ready">{{ validationIssue }}</span>
          <span v-else>Ready to publish on Bradbury</span>
        </div>
        <button class="primary-button" type="submit" :disabled="submitting">
          {{ !isConnected ? "Connect to continue" : submitting ? "Submitting..." : "Create project" }}
          <span v-if="submitting" class="button-spinner"></span>
          <ArrowRight :size="17" />
        </button>
      </footer>
    </form>
  </div>
</template>
