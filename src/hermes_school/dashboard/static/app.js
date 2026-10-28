const root = document.documentElement;
root.dataset.theme = localStorage.getItem('theme') || 'light';
document.querySelector('#theme')?.addEventListener('click', () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', root.dataset.theme);
});
document.querySelector('#calendar-toggle')?.addEventListener('click', () => {
  const list = document.querySelector('.record-list');
  list.classList.toggle('calendar');
  for (const article of list.querySelectorAll('.record')) {
    if (!article.querySelector('.day-label')) {
      const label = document.createElement('strong');
      label.className = 'day-label';
      label.textContent = article.dataset.date.slice(0, 10);
      article.prepend(label);
    }
  }
});
