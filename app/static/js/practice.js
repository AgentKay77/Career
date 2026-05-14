// Story practice mode controller (Alpine component).

function practiceController(storyId) {
  return {
    revealed: [],
    logged: false,
    reveal(section) {
      if (!this.revealed.includes(section)) {
        this.revealed.push(section);
      }
    },
    async logPractice() {
      const fd = new FormData();
      fd.set("csrf_token", CSRF_TOKEN);
      try {
        await fetch(`/stories/${storyId}/practice/log`, {
          method: "POST",
          body: fd,
          headers: { "HX-Request": "true" },
        });
        this.logged = true;
      } catch (e) {
        console.error(e);
      }
    },
  };
}
window.practiceController = practiceController;
