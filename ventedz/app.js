/* ============================================
   VENTE DZ — Application JavaScript
   ============================================ */

(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────
  const API_BASE = '/dz/api';

  // ─── State ───────────────────────────────────────────
  let allProducts = [];
  let allCategories = [];
  let settings = { usd_to_dzd: 0, profit_per_usd: 0 };
  let activeCategory = null;
  let searchQuery = '';
  let currentProduct = null;
  let statusPollTimer = null;

  // ─── Utilities ───────────────────────────────────────

  /**
   * Format price in DZD with thousands separator
   */
  function formatPrice(priceUsd) {
    const dzd = Math.ceil(priceUsd * (settings.usd_to_dzd + settings.profit_per_usd));
    return formatDZD(dzd);
  }

  function formatDZD(amount) {
    const formatted = amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return formatted + ' د.ج';
  }

  function calcDZD(priceUsd) {
    return Math.ceil(priceUsd * (settings.usd_to_dzd + settings.profit_per_usd));
  }

  /**
   * Get URL query parameter
   */
  function getParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  }

  /**
   * API fetch helper with error handling
   */
  async function apiFetch(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const config = {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    };
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }
    const response = await fetch(url, config);
    if (!response.ok) {
      let errMsg = `Erreur ${response.status}`;
      try {
        const errData = await response.json();
        if (errData.error) errMsg = errData.error;
        if (errData.detail) errMsg = errData.detail;
      } catch (_) {}
      throw new Error(errMsg);
    }
    return response.json();
  }

  /**
   * Show/hide elements
   */
  function show(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  }

  function hide(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  }

  /**
   * Toast notification
   */
  function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'toast ' + type;
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });
    setTimeout(() => {
      toast.classList.remove('visible');
    }, 3000);
  }

  /**
   * Copy text to clipboard
   */
  async function copyToClipboard(text, btnEl) {
    try {
      await navigator.clipboard.writeText(text);
      if (btnEl) {
        btnEl.classList.add('copied');
        btnEl.textContent = '✓';
        setTimeout(() => {
          btnEl.classList.remove('copied');
          btnEl.textContent = '📋';
        }, 2000);
      }
      showToast('Copié dans le presse-papiers !');
    } catch (err) {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast('Copié !');
    }
  }

  /**
   * Launch confetti animation
   */
  function launchConfetti() {
    const container = document.getElementById('confettiContainer');
    if (!container) return;
    const colors = ['#00c853', '#1db954', '#ffd700', '#e74c3c', '#3498db', '#9b59b6', '#e67e22', '#ffffff'];
    for (let i = 0; i < 80; i++) {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.left = Math.random() * 100 + '%';
      piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
      piece.style.width = (Math.random() * 8 + 4) + 'px';
      piece.style.height = (Math.random() * 8 + 4) + 'px';
      piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
      piece.style.animationDuration = (Math.random() * 2 + 2) + 's';
      piece.style.animationDelay = (Math.random() * 1.5) + 's';
      container.appendChild(piece);
    }
    // Clean up after animation
    setTimeout(() => {
      container.innerHTML = '';
    }, 5000);
  }

  /**
   * Render skeleton loading cards
   */
  function renderSkeletons(count = 8) {
    const grid = document.getElementById('productGrid');
    if (!grid) return;
    let html = '';
    for (let i = 0; i < count; i++) {
      html += `
        <div class="skeleton-card">
          <div class="skeleton skeleton-image"></div>
          <div class="skeleton-body">
            <div class="skeleton skeleton-text short"></div>
            <div class="skeleton skeleton-text medium"></div>
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-price"></div>
          </div>
        </div>
      `;
    }
    grid.innerHTML = html;
  }

  // ─── Product image placeholders ──────────────────────
  const categoryGradients = [
    'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
    'linear-gradient(135deg, #2d1b69, #1a1a2e, #0d1137)',
    'linear-gradient(135deg, #1a2a1a, #0a2a0a, #1a3a1a)',
    'linear-gradient(135deg, #2a1a1a, #3a1a1a, #1a0a0a)',
    'linear-gradient(135deg, #1a1a3a, #0a0a2a, #1a2a4a)',
    'linear-gradient(135deg, #2a2a1a, #3a3a0a, #1a1a0a)',
  ];

  function getGradient(index) {
    return categoryGradients[index % categoryGradients.length];
  }

  const categoryIcons = {
    default: '🎮',
  };

  // ─── CATALOG PAGE ────────────────────────────────────

  async function loadCatalog() {
    const grid = document.getElementById('productGrid');
    if (!grid) return;

    hide('emptyState');
    hide('errorState');
    show('productGrid');
    renderSkeletons(8);

    try {
      const data = await apiFetch('/products');
      allProducts = data.products || [];
      allCategories = data.categories || [];
      settings = data.settings || settings;

      renderCategories();
      renderProducts();
    } catch (err) {
      hide('productGrid');
      show('errorState');
      const errMsg = document.getElementById('errorMessage');
      if (errMsg) errMsg.textContent = err.message;
    }
  }

  function renderCategories() {
    const bar = document.getElementById('categoriesBar');
    if (!bar) return;

    let html = `<button class="category-pill active" data-id="all" onclick="filterCategory('all', this)">🏠 Tous</button>`;
    allCategories.forEach((cat) => {
      const emoji = cat.emoji || '📁';
      html += `<button class="category-pill" data-id="${cat.id}" onclick="filterCategory(${cat.id}, this)">${emoji} ${cat.name}</button>`;
    });
    bar.innerHTML = html;
  }

  window.filterCategory = function (id, btnEl) {
    activeCategory = id === 'all' ? null : id;
    // Update active pill
    document.querySelectorAll('.category-pill').forEach((p) => p.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    renderProducts();
  };

  window.resetFilters = function () {
    activeCategory = null;
    searchQuery = '';
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    document.querySelectorAll('.category-pill').forEach((p) => p.classList.remove('active'));
    const allPill = document.querySelector('.category-pill[data-id="all"]');
    if (allPill) allPill.classList.add('active');
    renderProducts();
  };

  function renderProducts() {
    const grid = document.getElementById('productGrid');
    if (!grid) return;

    let filtered = allProducts;

    // Filter by category
    if (activeCategory !== null) {
      filtered = filtered.filter((p) => p.category_id === activeCategory);
    }

    // Filter by search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.dz_description && p.dz_description.toLowerCase().includes(q)) ||
          (p.category_name && p.category_name.toLowerCase().includes(q))
      );
    }

    // Update count
    const countEl = document.getElementById('resultsCount');
    if (countEl) {
      countEl.textContent = `${filtered.length} produit${filtered.length !== 1 ? 's' : ''} trouvé${filtered.length !== 1 ? 's' : ''}`;
    }

    if (filtered.length === 0) {
      hide('productGrid');
      show('emptyState');
      return;
    }

    hide('emptyState');
    show('productGrid');

    let html = '';
    filtered.forEach((product, i) => {
      const price = formatPrice(product.price_usd);
      const hasImage = product.dz_image_url && product.dz_image_url.trim();
      const inStock = product.stock_count > 0;
      const stockBadge = inStock
        ? `<div class="stock-badge in-stock"><span class="dot"></span> En stock</div>`
        : `<div class="stock-badge out-of-stock">Épuisé</div>`;

      const imageContent = hasImage
        ? `<img src="${product.dz_image_url}" alt="${product.name}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
        : '';

      const placeholderDisplay = hasImage ? 'none' : 'flex';

      html += `
        <a href="product.html?id=${product.id}" class="product-card" style="text-decoration:none; color:inherit;">
          <div class="product-card-image" style="background: ${getGradient(i)}">
            ${imageContent}
            <span class="placeholder-icon" style="display:${placeholderDisplay}; align-items:center; justify-content:center; width:100%; height:100%; position:absolute; top:0; left:0;">🎮</span>
            ${stockBadge}
          </div>
          <div class="product-card-body">
            <div class="product-card-category">${product.category_name || ''}</div>
            <div class="product-card-name">${escapeHtml(product.name)}</div>
            <div class="product-card-description">${escapeHtml(product.dz_description || '')}</div>
            <div class="product-card-footer">
              <div class="product-card-price">${price}</div>
              <span class="btn btn-ghost btn-sm">Voir →</span>
            </div>
          </div>
        </a>
      `;
    });

    grid.innerHTML = html;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Search debounce
  function initSearch() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    let debounceTimer;
    input.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchQuery = e.target.value;
        renderProducts();
      }, 250);
    });
  }

  // ─── PRODUCT DETAIL PAGE ─────────────────────────────

  async function loadProduct() {
    const id = getParam('id');
    if (!id) {
      hide('loadingState');
      show('errorState');
      return;
    }

    try {
      const data = await apiFetch(`/products/${id}`);
      currentProduct = data;

      // Also need settings for price calculation
      try {
        const catalogData = await apiFetch('/products');
        settings = catalogData.settings || settings;
      } catch (_) {}

      renderProductDetail();
    } catch (err) {
      hide('loadingState');
      show('errorState');
      const errMsg = document.getElementById('errorMessage');
      if (errMsg) errMsg.textContent = err.message;
    }
  }

  function renderProductDetail() {
    const p = currentProduct;
    if (!p) return;

    hide('loadingState');
    show('productDetail');

    // Image
    const imgContainer = document.getElementById('productImageContainer');
    const placeholder = document.getElementById('productPlaceholder');
    if (p.dz_image_url && p.dz_image_url.trim()) {
      const img = document.createElement('img');
      img.src = p.dz_image_url;
      img.alt = p.name;
      img.onerror = function () {
        this.style.display = 'none';
        placeholder.style.display = 'block';
      };
      placeholder.style.display = 'none';
      imgContainer.insertBefore(img, placeholder);
    }

    // Category
    const catEl = document.getElementById('productCategory');
    catEl.textContent = (p.category_emoji || '📁') + ' ' + (p.category_name || 'Produit');

    // Name
    document.getElementById('productName').textContent = p.name;

    // Description
    document.getElementById('productDescription').textContent = p.dz_description || p.description || '';

    // Price
    const unitPrice = calcDZD(p.price_usd);
    document.getElementById('productPrice').textContent = formatDZD(unitPrice);

    // Stock
    const stockEl = document.getElementById('productStock');
    const stockText = document.getElementById('productStockText');
    const inStock = p.stock_count > 0;

    if (inStock) {
      stockEl.className = 'product-stock-info available';
      stockText.textContent = `${p.stock_count} en stock`;
    } else {
      stockEl.className = 'product-stock-info unavailable';
      stockText.textContent = 'Rupture de stock';
    }

    // Quantity
    const qtyInput = document.getElementById('qtyInput');
    qtyInput.max = p.stock_count || 0;
    qtyInput.value = 1;
    updateQtyButtons();
    updateTotal();

    // Disable buy button if out of stock
    const buyBtn = document.getElementById('buyBtn');
    if (!inStock) {
      buyBtn.disabled = true;
      buyBtn.textContent = 'Indisponible';
      buyBtn.classList.remove('btn-gradient');
      buyBtn.classList.add('btn-outline');
      hide('qtySection');
      hide('totalSection');
    }

    // Update page title
    document.title = p.name + ' — VENTE DZ';
  }

  window.changeQty = function (delta) {
    const qtyInput = document.getElementById('qtyInput');
    let val = parseInt(qtyInput.value) || 1;
    val += delta;
    val = Math.max(1, Math.min(val, parseInt(qtyInput.max) || 1));
    qtyInput.value = val;
    updateQtyButtons();
    updateTotal();
  };

  window.onQtyChange = function () {
    const qtyInput = document.getElementById('qtyInput');
    let val = parseInt(qtyInput.value) || 1;
    val = Math.max(1, Math.min(val, parseInt(qtyInput.max) || 1));
    qtyInput.value = val;
    updateQtyButtons();
    updateTotal();
  };

  function updateQtyButtons() {
    const qtyInput = document.getElementById('qtyInput');
    if (!qtyInput) return;
    const val = parseInt(qtyInput.value) || 1;
    const max = parseInt(qtyInput.max) || 1;
    const minusBtn = document.getElementById('qtyMinus');
    const plusBtn = document.getElementById('qtyPlus');
    if (minusBtn) minusBtn.disabled = val <= 1;
    if (plusBtn) plusBtn.disabled = val >= max;
  }

  function updateTotal() {
    if (!currentProduct) return;
    const qtyInput = document.getElementById('qtyInput');
    const qty = parseInt(qtyInput.value) || 1;
    const unitPrice = calcDZD(currentProduct.price_usd);
    const total = unitPrice * qty;
    const totalEl = document.getElementById('totalPrice');
    if (totalEl) totalEl.textContent = formatDZD(total);
  }

  window.goToCheckout = function () {
    if (!currentProduct) return;
    const qty = document.getElementById('qtyInput').value;
    window.location.href = `checkout.html?id=${currentProduct.id}&qty=${qty}`;
  };

  // ─── CHECKOUT PAGE ──────────────────────────────────

  async function loadCheckout() {
    const productId = getParam('id');
    const qty = parseInt(getParam('qty')) || 1;

    if (!productId) {
      hide('loadingState');
      show('errorState');
      return;
    }

    try {
      const product = await apiFetch(`/products/${productId}`);
      currentProduct = product;

      // Get settings
      try {
        const catalogData = await apiFetch('/products');
        settings = catalogData.settings || settings;
      } catch (_) {}

      renderCheckout(product, qty);
    } catch (err) {
      hide('loadingState');
      show('errorState');
      const errMsg = document.getElementById('errorMessage');
      if (errMsg) errMsg.textContent = err.message;
    }
  }

  function renderCheckout(product, qty) {
    hide('loadingState');
    show('checkoutContent');

    const unitPrice = calcDZD(product.price_usd);
    const total = unitPrice * qty;

    document.getElementById('summaryName').textContent = product.name;
    document.getElementById('summaryUnitPrice').textContent = formatDZD(unitPrice);
    document.getElementById('summaryQty').textContent = qty;
    document.getElementById('summaryTotal').textContent = formatDZD(total);

    // Store qty for form submission
    document.getElementById('checkoutForm').dataset.productId = product.id;
    document.getElementById('checkoutForm').dataset.qty = qty;

    document.title = 'Paiement — ' + product.name + ' — VENTE DZ';
  }

  window.handleCheckout = async function (e) {
    e.preventDefault();

    const form = document.getElementById('checkoutForm');
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();

    // Validate
    let valid = true;

    if (!name || name.length < 3) {
      document.getElementById('nameError').classList.add('visible');
      document.getElementById('customerName').classList.add('error');
      valid = false;
    } else {
      document.getElementById('nameError').classList.remove('visible');
      document.getElementById('customerName').classList.remove('error');
    }

    // Phone validation: Algerian format
    const phoneClean = phone.replace(/\s/g, '');
    const phoneRegex = /^(0[567]\d{8}|\+213[567]\d{8})$/;
    if (!phoneRegex.test(phoneClean)) {
      document.getElementById('phoneError').classList.add('visible');
      document.getElementById('customerPhone').classList.add('error');
      valid = false;
    } else {
      document.getElementById('phoneError').classList.remove('visible');
      document.getElementById('customerPhone').classList.remove('error');
    }

    if (!valid) return false;

    // Show loading overlay
    show('checkoutOverlay');
    document.getElementById('payBtn').disabled = true;

    try {
      const result = await apiFetch('/checkout', {
        method: 'POST',
        body: {
          product_id: parseInt(form.dataset.productId),
          quantity: parseInt(form.dataset.qty),
          customer_name: name,
          customer_phone: phoneClean,
        },
      });

      if (result.payment_url) {
        window.location.href = result.payment_url;
      } else {
        hide('checkoutOverlay');
        document.getElementById('payBtn').disabled = false;
        showToast('Erreur: URL de paiement manquante', 'error');
      }
    } catch (err) {
      hide('checkoutOverlay');
      document.getElementById('payBtn').disabled = false;
      showToast('Erreur: ' + err.message, 'error');
    }

    return false;
  };

  // ─── ORDER STATUS PAGE ───────────────────────────────

  async function loadOrderStatus() {
    const ref = getParam('ref');
    if (!ref) {
      hide('loadingState');
      show('errorState');
      return;
    }

    checkOrderStatus(ref);
  }

  async function checkOrderStatus(ref) {
    show('loadingState');
    hide('successState');
    hide('pendingState');
    hide('failedState');
    hide('errorState');

    try {
      const data = await apiFetch(`/order-status/${ref}`);
      hide('loadingState');

      const status = (data.status || '').toUpperCase();

      if (status === 'CONFIRMED' || status === 'DELIVERED') {
        renderSuccess(ref, data);
      } else if (status === 'PENDING' || status === 'PROCESSING') {
        renderPending(ref);
        // Auto-retry in 5 seconds
        statusPollTimer = setTimeout(() => checkOrderStatus(ref), 5000);
      } else if (status === 'FAILED' || status === 'CANCELLED' || status === 'EXPIRED') {
        renderFailed(ref, data);
      } else {
        // Unknown status - treat as pending
        renderPending(ref);
        statusPollTimer = setTimeout(() => checkOrderStatus(ref), 5000);
      }
    } catch (err) {
      hide('loadingState');
      show('errorState');
      const errMsg = document.getElementById('errorMessage');
      if (errMsg) errMsg.textContent = err.message;
    }
  }

  function renderSuccess(ref, data) {
    show('successState');
    document.getElementById('successRef').textContent = '📦 ' + ref;

    // Render delivered items
    const itemsContainer = document.getElementById('deliveredItems');
    const items = data.items || [];

    if (items.length > 0) {
      let html = '<h3 class="section-title" style="margin-bottom:16px;">🎁 Vos produits</h3>';
      items.forEach((item, i) => {
        html += `
          <div class="delivered-item">
            <div class="delivered-item-content">
              <div class="delivered-item-label">Produit #${i + 1}</div>
              <div class="delivered-item-value" id="item-${i}">${escapeHtml(item)}</div>
            </div>
            <button class="copy-btn" onclick="window.__copyItem(${i}, this)" title="Copier">📋</button>
          </div>
        `;
      });
      itemsContainer.innerHTML = html;
    } else {
      itemsContainer.innerHTML = '<p class="text-muted text-center mt-16">Les détails de votre commande vous seront envoyés par téléphone.</p>';
    }

    // Confetti!
    launchConfetti();
  }

  window.__copyItem = function (index, btn) {
    const el = document.getElementById('item-' + index);
    if (el) copyToClipboard(el.textContent, btn);
  };

  function renderPending(ref) {
    show('pendingState');
    document.getElementById('pendingRef').textContent = '📦 ' + ref;
  }

  function renderFailed(ref, data) {
    show('failedState');
    document.getElementById('failedRef').textContent = '📦 ' + ref;
    if (data && data.message) {
      document.getElementById('failedMessage').textContent = data.message;
    }
  }

  // ─── Scroll to top button ───────────────────────────

  function initScrollTop() {
    const btn = document.getElementById('scrollTop');
    if (!btn) return;
    window.addEventListener('scroll', () => {
      if (window.scrollY > 400) {
        btn.classList.add('visible');
      } else {
        btn.classList.remove('visible');
      }
    });
  }

  // ─── ROUTER ──────────────────────────────────────────

  function init() {
    const path = window.location.pathname;

    initScrollTop();

    if (path.endsWith('index.html') || path.endsWith('/') || path.endsWith('/ventedz/') || path.endsWith('/ventedz')) {
      // Catalog page
      loadCatalog();
      initSearch();
    } else if (path.endsWith('product.html')) {
      // Product detail page
      loadProduct();
    } else if (path.endsWith('checkout.html')) {
      // Checkout page
      loadCheckout();
    } else if (path.endsWith('order-status.html')) {
      // Order status page
      loadOrderStatus();
    }
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (statusPollTimer) clearTimeout(statusPollTimer);
  });

  // Clear form errors on input
  document.addEventListener('input', (e) => {
    if (e.target.classList.contains('form-input') && e.target.classList.contains('error')) {
      e.target.classList.remove('error');
      const errorEl = e.target.parentElement.querySelector('.form-error');
      if (errorEl) errorEl.classList.remove('visible');
    }
  });

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
