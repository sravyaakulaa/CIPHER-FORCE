document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".nav-links");
  if (toggle && nav) {
    toggle.addEventListener("click", () => nav.classList.toggle("nav-open"));
  }

  const fileInput = document.getElementById("resume-file");
  const fileLabel = document.getElementById("file-label");
  if (fileInput && fileLabel) {
    fileInput.addEventListener("change", () => {
      fileLabel.textContent = fileInput.files.length
        ? fileInput.files[0].name
        : "Choose a PDF file";
    });
  }

  document.querySelectorAll(".flash").forEach((flash) => {
    window.setTimeout(() => {
      flash.classList.add("flash-fade");
      window.setTimeout(() => flash.remove(), 400);
    }, 5000);
  });
});
