// Wait for the page to load and for the jtd theme object to be available
document.addEventListener('DOMContentLoaded', function() {
  
  // The theme's own JS might initialize after this script, so we poll for `jtd.setTheme`
  function initializeThemeSwitcher() {
    if (typeof jtd === 'undefined' || typeof jtd.setTheme !== 'function') {
      setTimeout(initializeThemeSwitcher, 50); // Try again in 50ms
      return;
    }

    const themeSwitcher = {
      // Use a sensible default, then check localStorage
      currentTheme: (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light',
      button: null,

      init: function() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
          this.currentTheme = savedTheme;
        }

        this.button = document.createElement('button');
        this.button.className = 'btn js-toggle-theme';
        this.button.addEventListener('click', () => this.toggleTheme());

        const siteHeader = document.querySelector('.site-header');
        if (siteHeader) {
          siteHeader.appendChild(this.button);
        }

        // Apply theme on initial load
        this.applyTheme();
      },

      applyTheme: function() {
        // Use the official just-the-docs function to set the theme
        jtd.setTheme(this.currentTheme);
        
        // Update the button icon and aria-label
        if (this.currentTheme === 'dark') {
          this.button.innerHTML = '☀️';
          this.button.setAttribute('aria-label', 'Switch to light theme');
        } else {
          this.button.innerHTML = '🌙';
          this.button.setAttribute('aria-label', 'Switch to dark theme');
        }
      },

      toggleTheme: function() {
        this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', this.currentTheme);
        this.applyTheme();
      }
    };

    themeSwitcher.init();
  }
  
  initializeThemeSwitcher();
});