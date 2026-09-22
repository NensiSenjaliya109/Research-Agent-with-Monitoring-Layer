document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('robotBg');
  if (container) {
    // Determine the JSON path based on static serving or local index file
    const path = window.location.pathname.includes('/static/') 
      ? '/static/assets/robot-sad-mood.json' 
      : 'assets/robot-sad-mood.json';

    lottie.loadAnimation({
      container: container,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: path
    });
  }
});
