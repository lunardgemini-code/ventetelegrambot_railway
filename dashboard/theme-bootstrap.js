(() => {
    'use strict';

    const root = document.documentElement;
    const validAppearances = new Set(['liquid', 'standard', 'auto']);

    function readPreference(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (_error) {
            return null;
        }
    }

    const savedAppearance = readPreference('ventebot_appearance');
    const appearance = validAppearances.has(savedAppearance) ? savedAppearance : 'liquid';
    const savedTheme = readPreference('vb_theme');
    const systemTheme = window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    const theme = appearance === 'auto'
        ? systemTheme
        : (savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'dark');

    root.dataset.appearance = appearance;
    root.dataset.theme = theme;
    root.dataset.reduceTransparency = readPreference('ventebot_reduce_transparency') === 'true'
        ? 'true'
        : 'false';
    root.style.colorScheme = theme;
})();
