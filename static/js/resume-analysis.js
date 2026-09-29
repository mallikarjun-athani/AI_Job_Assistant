document.querySelectorAll('[data-analysis-form]').forEach((form) => {
    form.addEventListener('submit', () => {
        const button = form.querySelector('button[type="submit"]');
        const loading = form.querySelector('.analysis-loading');

        if (button) {
            button.disabled = true;
            button.textContent = 'Analyzing...';
        }
        if (loading) {
            loading.hidden = false;
        }
    });
});