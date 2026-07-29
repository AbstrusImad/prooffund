const SEEDED_PROJECT_IMAGES = new Set(
  Array.from({ length: 9 }, (_, index) => `PF-${String(index + 1).padStart(4, "0")}`),
);
const publicAsset = (path) => `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;

export const projectImage = (project) =>
  SEEDED_PROJECT_IMAGES.has(project?.id)
    ? publicAsset(`/projects/${project.id.toLowerCase()}.jpg`)
    : project?.image_url || publicAsset("/projects/pf-0001.jpg");

export const useImageFallback = (event) => {
  if (!event?.target || event.target.dataset.fallbackApplied) return;
  event.target.dataset.fallbackApplied = "true";
  event.target.src = publicAsset("/projects/pf-0001.jpg");
};
