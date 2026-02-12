/* ========================================================
   ShopVerse Frontend — Vanilla JS SPA
   ======================================================== */

// ===== CONFIG =====
const API_BASE = ''; // Same origin, via NGINX gateway
const API = {
    auth: `${API_BASE}/api/v1/auth`,
    users: `${API_BASE}/api/v1/users`,
    products: `${API_BASE}/api/v1/products`,
    categories: `${API_BASE}/api/v1/categories`,
    cart: `${API_BASE}/api/v1/cart`,
    orders: `${API_BASE}/api/v1/orders`,
    payments: `${API_BASE}/api/v1/payments`,
};

// ===== API CLIENT =====
const api = {
    getToken() { return localStorage.getItem('access_token'); },
    getRefresh() { return localStorage.getItem('refresh_token'); },
    setTokens(access, refresh) {
        localStorage.setItem('access_token', access);
        if (refresh) localStorage.setItem('refresh_token', refresh);
    },
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },
    getUser() {
        try { return JSON.parse(localStorage.getItem('user')); } catch { return null; }
    },
    setUser(u) { localStorage.setItem('user', JSON.stringify(u)); },

    async request(url, opts = {}) {
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
        const token = this.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        try {
            let res = await fetch(url, { ...opts, headers });

            // Token refresh on 401
            if (res.status === 401 && this.getRefresh()) {
                const refreshRes = await fetch(`${API.auth}/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: this.getRefresh() }),
                });
                if (refreshRes.ok) {
                    const data = await refreshRes.json();
                    this.setTokens(data.access_token, data.refresh_token);
                    headers['Authorization'] = `Bearer ${data.access_token}`;
                    res = await fetch(url, { ...opts, headers });
                } else {
                    this.clearTokens();
                    navigate('/login');
                    throw new Error('Session expired');
                }
            }

            const json = await res.json().catch(() => null);

            if (!res.ok) {
                const msg = json?.detail || json?.message || `Error ${res.status}`;
                throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
            }
            return json;
        } catch (err) {
            if (err.message === 'Session expired') throw err;
            if (err.name === 'TypeError') throw new Error('Network error — is the backend running?');
            throw err;
        }
    },

    get(url) { return this.request(url); },
    post(url, body) { return this.request(url, { method: 'POST', body: JSON.stringify(body) }); },
    put(url, body) { return this.request(url, { method: 'PUT', body: JSON.stringify(body) }); },
    del(url) { return this.request(url, { method: 'DELETE' }); },
};

// ===== TOAST =====
function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3500);
}

// ===== ROUTER =====
const routes = {
    '/': { template: 'tmpl-home', init: initHome },
    '/products': { template: 'tmpl-products', init: initProducts },
    '/product/:id': { template: 'tmpl-product-detail', init: initProductDetail },
    '/cart': { template: 'tmpl-cart', init: initCart },
    '/checkout': { template: 'tmpl-checkout', init: initCheckout },
    '/orders': { template: 'tmpl-orders', init: initOrders },
    '/login': { template: 'tmpl-login', init: initLogin },
    '/register': { template: 'tmpl-register', init: initRegister },
    '/profile': { template: 'tmpl-profile', init: initProfile },
};

function navigate(path) { window.location.hash = path; }

function matchRoute(hash) {
    const path = hash.replace(/^#/, '') || '/';
    // Exact match first
    if (routes[path]) return { route: routes[path], params: {} };
    // Parametric match
    for (const [pattern, route] of Object.entries(routes)) {
        const patternParts = pattern.split('/');
        const pathParts = path.split('/');
        if (patternParts.length !== pathParts.length) continue;
        const params = {};
        let match = true;
        for (let i = 0; i < patternParts.length; i++) {
            if (patternParts[i].startsWith(':')) {
                params[patternParts[i].slice(1)] = pathParts[i];
            } else if (patternParts[i] !== pathParts[i]) {
                match = false; break;
            }
        }
        if (match) return { route, params };
    }
    return null;
}

function router() {
    const matched = matchRoute(window.location.hash);
    if (!matched) { navigate('/'); return; }
    const { route, params } = matched;

    // Auth guard
    const authPages = ['/orders', '/checkout', '/profile'];
    const currentPath = window.location.hash.replace(/^#/, '') || '/';
    if (authPages.includes(currentPath) && !api.getToken()) {
        toast('Please login first', 'error');
        navigate('/login');
        return;
    }

    // Render template
    const template = document.getElementById(route.template);
    const app = document.getElementById('app');
    app.innerHTML = '';
    app.appendChild(template.content.cloneNode(true));

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const page = currentPath.split('/')[1] || 'home';
    document.querySelectorAll(`.nav-link`).forEach(l => {
        if (l.dataset.page === page || (page === '' && l.dataset.page === 'home')) {
            l.classList.add('active');
        }
    });

    // Close mobile menu
    document.getElementById('navbar').classList.remove('mobile-open');

    // Scroll to top
    window.scrollTo(0, 0);

    // Init page
    route.init(params);
}

// ===== UI HELPERS =====
function updateNavbar() {
    const user = api.getUser();
    const guestNav = document.getElementById('nav-guest');
    const userNav = document.getElementById('nav-user');
    const ordersLink = document.getElementById('nav-orders');

    if (user && api.getToken()) {
        guestNav.style.display = 'none';
        userNav.style.display = 'flex';
        ordersLink.style.display = '';
        document.getElementById('nav-username').textContent = user.first_name || 'User';
        document.getElementById('nav-avatar').textContent = (user.first_name?.[0] || 'U').toUpperCase();
    } else {
        guestNav.style.display = '';
        userNav.style.display = 'none';
        ordersLink.style.display = 'none';
    }
}

function updateCartBadge(count) {
    const badge = document.getElementById('cart-badge');
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = '';
    } else {
        badge.style.display = 'none';
    }
}

function productCardHTML(p) {
    const img = p.images && p.images.length > 0 && p.images[0]
        ? `<img src="${p.images[0]}" alt="${esc(p.name)}">`
        : `<span class="placeholder-icon">📦</span>`;
    const compare = p.compare_at_price ? `<span class="price-compare">$${num(p.compare_at_price)}</span>` : '';
    const featured = p.is_featured ? `<span class="featured-badge">Featured</span>` : '';
    const stock = p.stock_quantity > 0
        ? `<span class="stock-badge stock-in">In Stock</span>`
        : `<span class="stock-badge stock-out">Out of Stock</span>`;

    return `
        <div class="product-card" onclick="navigate('/product/${p.id}')">
            <div class="product-card-img">${featured}${img}</div>
            <div class="product-card-body">
                <div class="product-card-name">${esc(p.name)}</div>
                <div class="product-card-price">
                    <span class="price-current">$${num(p.price)}</span>
                    ${compare}
                </div>
                <div class="product-card-footer">
                    ${stock}
                    <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); addToCart(${p.id}, 1)">Add to Cart</button>
                </div>
            </div>
        </div>`;
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
function num(v) { return parseFloat(v || 0).toFixed(2); }

// ===== CART HELPER =====
async function addToCart(productId, quantity = 1) {
    try {
        const res = await api.post(`${API.cart}/items`, { product_id: productId, quantity });
        const data = res.data || res;
        updateCartBadge(data.total_items || 0);
        toast('Added to cart!', 'success');
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function fetchCartCount() {
    try {
        const res = await api.get(`${API.cart}/`);
        const data = res.data || res;
        updateCartBadge(data.total_items || (data.items ? data.items.length : 0));
    } catch { /* silent */ }
}

// ===== PAGE: HOME =====
async function initHome() {
    // Featured products
    try {
        const res = await api.get(`${API.products}/?is_featured=true&size=4`);
        const products = res.data || res || [];
        const container = document.getElementById('featured-products');
        if (Array.isArray(products) && products.length > 0) {
            container.innerHTML = products.map(productCardHTML).join('');
        } else {
            container.innerHTML = '<p style="color:var(--text-secondary);">No featured products yet.</p>';
        }
    } catch (err) {
        document.getElementById('featured-products').innerHTML = `<p style="color:var(--text-muted);">Unable to load products. ${esc(err.message)}</p>`;
    }

    // Categories
    try {
        const res = await api.get(`${API.categories}/`);
        const cats = res.data || res || [];
        const container = document.getElementById('home-categories');
        const icons = ['🖥️', '📱', '👕', '👟', '📚', '🎮', '🏠', '💄', '🔧', '🎵'];
        if (Array.isArray(cats) && cats.length > 0) {
            container.innerHTML = cats.map((c, i) => `
                <a href="#/products?category=${c.id}" class="category-card">
                    <div class="category-icon">${icons[i % icons.length]}</div>
                    <div class="category-name">${esc(c.name)}</div>
                </a>
            `).join('');
        } else {
            container.innerHTML = '<p style="color:var(--text-secondary);">No categories yet.</p>';
        }
    } catch {
        document.getElementById('home-categories').innerHTML = '<p style="color:var(--text-muted);">Unable to load categories.</p>';
    }
}

// ===== PAGE: PRODUCTS =====
let currentPage = 1;
async function initProducts() {
    // Load categories into filter
    try {
        const res = await api.get(`${API.categories}/`);
        const cats = res.data || res || [];
        const sel = document.getElementById('filter-category');
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
    } catch { /* silent */ }

    // Parse query params from hash
    const hash = window.location.hash;
    const qIdx = hash.indexOf('?');
    const params = new URLSearchParams(qIdx >= 0 ? hash.slice(qIdx) : '');

    if (params.get('category')) document.getElementById('filter-category').value = params.get('category');
    if (params.get('search')) document.getElementById('search-input').value = params.get('search');
    if (params.get('featured') === 'true') { /* could set a filter */ }

    currentPage = 1;
    loadProducts();

    // Events
    document.getElementById('btn-apply-filters').addEventListener('click', () => { currentPage = 1; loadProducts(); });
    document.getElementById('btn-search').addEventListener('click', () => { currentPage = 1; loadProducts(); });
    document.getElementById('search-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') { currentPage = 1; loadProducts(); } });
}

async function loadProducts() {
    const list = document.getElementById('product-list');
    list.innerHTML = '<div class="loading-spinner"></div>';

    const category = document.getElementById('filter-category')?.value || '';
    const minPrice = document.getElementById('filter-min-price')?.value || '';
    const maxPrice = document.getElementById('filter-max-price')?.value || '';
    const inStock = document.getElementById('filter-in-stock')?.checked || false;
    const sortVal = document.getElementById('filter-sort')?.value || 'created_at:desc';
    const search = document.getElementById('search-input')?.value || '';
    const [sortBy, sortOrder] = sortVal.split(':');

    const params = new URLSearchParams({
        page: currentPage,
        size: 12,
        sort_by: sortBy,
        sort_order: sortOrder,
    });
    if (category) params.set('category_id', category);
    if (minPrice) params.set('min_price', minPrice);
    if (maxPrice) params.set('max_price', maxPrice);
    if (inStock) params.set('in_stock_only', 'true');
    if (search) params.set('search', search);

    try {
        const res = await api.get(`${API.products}/?${params}`);
        const products = res.data || res || [];
        if (Array.isArray(products) && products.length > 0) {
            list.innerHTML = products.map(productCardHTML).join('');
            // Simple pagination (if we got full page, show next)
            const pag = document.getElementById('pagination');
            pag.innerHTML = '';
            if (currentPage > 1) {
                pag.innerHTML += `<button class="page-btn" onclick="currentPage--; loadProducts()">← Prev</button>`;
            }
            pag.innerHTML += `<span class="page-btn active">${currentPage}</span>`;
            if (products.length >= 12) {
                pag.innerHTML += `<button class="page-btn" onclick="currentPage++; loadProducts()">Next →</button>`;
            }
        } else {
            list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No products found</p></div>';
        }
    } catch (err) {
        list.innerHTML = `<div class="empty-state"><p>${esc(err.message)}</p></div>`;
    }
}

// ===== PAGE: PRODUCT DETAIL =====
async function initProductDetail(params) {
    const container = document.getElementById('product-detail');
    try {
        const res = await api.get(`${API.products}/${params.id}`);
        const p = res.data || res;

        const img = p.images && p.images.length > 0 && p.images[0]
            ? `<img src="${p.images[0]}" alt="${esc(p.name)}">`
            : `<span class="placeholder-icon">📦</span>`;
        const compare = p.compare_at_price ? `<span class="pd-compare">$${num(p.compare_at_price)}</span>` : '';

        container.innerHTML = `
            <div class="pd-image">${img}</div>
            <div class="pd-info">
                <div class="pd-category">${esc(p.category?.name || '')}</div>
                <h1 class="pd-name">${esc(p.name)}</h1>
                <div class="pd-prices">
                    <span class="pd-price">$${num(p.price)}</span>
                    ${compare}
                </div>
                <p class="pd-desc">${esc(p.description || 'No description available.')}</p>
                <div class="pd-meta">
                    <div class="pd-meta-item">
                        <div class="pd-meta-label">SKU</div>
                        <div class="pd-meta-value">${esc(p.sku || 'N/A')}</div>
                    </div>
                    <div class="pd-meta-item">
                        <div class="pd-meta-label">Stock</div>
                        <div class="pd-meta-value">${p.stock_quantity > 0 ? p.stock_quantity + ' available' : '<span style="color:var(--danger)">Out of Stock</span>'}</div>
                    </div>
                </div>
                <div class="pd-actions">
                    <div class="qty-control">
                        <button class="qty-btn" id="qty-minus">−</button>
                        <input class="qty-value" id="qty-input" type="number" value="1" min="1" max="${p.stock_quantity || 1}" readonly>
                        <button class="qty-btn" id="qty-plus">+</button>
                    </div>
                    <button class="btn btn-primary btn-lg" id="btn-add-to-cart" ${p.stock_quantity <= 0 ? 'disabled' : ''}>
                        Add to Cart
                    </button>
                </div>
            </div>
        `;

        // Quantity controls
        const qtyInput = document.getElementById('qty-input');
        document.getElementById('qty-minus').addEventListener('click', () => {
            let v = parseInt(qtyInput.value); if (v > 1) qtyInput.value = v - 1;
        });
        document.getElementById('qty-plus').addEventListener('click', () => {
            let v = parseInt(qtyInput.value);
            if (v < (p.stock_quantity || 1)) qtyInput.value = v + 1;
        });
        document.getElementById('btn-add-to-cart').addEventListener('click', () => {
            addToCart(p.id, parseInt(qtyInput.value));
        });
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>Product not found. ${esc(err.message)}</p></div>`;
    }
}

// ===== PAGE: CART =====
async function initCart() {
    const container = document.getElementById('cart-content');
    try {
        const res = await api.get(`${API.cart}/`);
        const cart = res.data || res;
        const items = cart.items || [];

        if (items.length === 0) {
            container.innerHTML = `
                <div class="cart-empty">
                    <div class="cart-empty-icon">🛒</div>
                    <h2>Your cart is empty</h2>
                    <p>Browse our products and add something you love!</p>
                    <a href="#/products" class="btn btn-primary">Continue Shopping</a>
                </div>`;
            updateCartBadge(0);
            return;
        }

        const subtotal = cart.subtotal || items.reduce((s, i) => s + parseFloat(i.price || 0) * i.quantity, 0);

        container.innerHTML = `
            <div class="cart-layout">
                <div class="cart-items">
                    ${items.map(item => `
                        <div class="cart-item" data-product-id="${item.product_id}">
                            <div class="cart-item-img">
                                ${item.image ? `<img src="${item.image}" alt="${esc(item.name)}">` : '<span style="font-size:1.5rem;">📦</span>'}
                            </div>
                            <div class="cart-item-info">
                                <div class="cart-item-name">${esc(item.name || `Product #${item.product_id}`)}</div>
                                <div class="cart-item-price">$${num(item.price)}</div>
                                <div class="cart-item-actions">
                                    <div class="qty-control">
                                        <button class="qty-btn" onclick="updateCartItem(${item.product_id}, ${item.quantity - 1})">−</button>
                                        <span class="qty-value">${item.quantity}</span>
                                        <button class="qty-btn" onclick="updateCartItem(${item.product_id}, ${item.quantity + 1})">+</button>
                                    </div>
                                    <button class="cart-item-remove" onclick="removeCartItem(${item.product_id})">✕ Remove</button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div class="cart-summary">
                    <h3>Order Summary</h3>
                    <div class="summary-row"><span>Subtotal (${items.reduce((s, i) => s + i.quantity, 0)} items)</span><span>$${num(subtotal)}</span></div>
                    <div class="summary-row"><span>Shipping</span><span>Calculated at checkout</span></div>
                    <div class="summary-row total"><span>Estimated Total</span><span>$${num(subtotal)}</span></div>
                    <a href="#/checkout" class="btn btn-primary btn-lg btn-block" style="margin-top:1.25rem;" ${!api.getToken() ? 'onclick="event.preventDefault(); toast(\'Please login to checkout\', \'error\'); navigate(\'/login\');"' : ''}>
                        Proceed to Checkout
                    </a>
                    <a href="#/products" class="btn btn-glass btn-block" style="margin-top:0.5rem;">Continue Shopping</a>
                </div>
            </div>`;

        updateCartBadge(cart.total_items || items.reduce((s, i) => s + i.quantity, 0));
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>Unable to load cart. ${esc(err.message)}</p></div>`;
    }
}

async function updateCartItem(productId, newQuantity) {
    try {
        if (newQuantity < 1) { await removeCartItem(productId); return; }
        await api.put(`${API.cart}/items/${productId}`, { quantity: newQuantity });
        initCart(); // Re-render
    } catch (err) { toast(err.message, 'error'); }
}

async function removeCartItem(productId) {
    try {
        await api.del(`${API.cart}/items/${productId}`);
        toast('Item removed', 'info');
        initCart();
    } catch (err) { toast(err.message, 'error'); }
}

// ===== PAGE: CHECKOUT =====
async function initCheckout() {
    // Load cart summary
    try {
        const res = await api.get(`${API.cart}/summary`);
        const summary = res.data || res;
        const summaryEl = document.getElementById('checkout-summary');
        summaryEl.innerHTML = `
            <div class="summary-row"><span>Subtotal</span><span>$${num(summary.subtotal)}</span></div>
            <div class="summary-row"><span>Tax</span><span>$${num(summary.tax)}</span></div>
            <div class="summary-row"><span>Shipping</span><span>$${num(summary.shipping)}</span></div>
            <div class="summary-row total"><span>Total</span><span>$${num(summary.total)}</span></div>
        `;
    } catch (err) {
        document.getElementById('checkout-summary').innerHTML = `<p style="color:var(--text-muted);">${esc(err.message)}</p>`;
    }

    // Form submit
    document.getElementById('checkout-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btn-place-order');
        btn.disabled = true;
        btn.textContent = 'Placing Order...';

        const form = e.target;
        const shipping = {
            street: form.street.value,
            city: form.city.value,
            state: form.state.value,
            postal_code: form.postal_code.value,
            country: form.country.value,
        };

        try {
            const res = await api.post(`${API.orders}/`, {
                shipping_address: shipping,
                billing_address: shipping, // same for simplicity
                notes: form.notes.value || '',
            });
            const order = res.data || res;
            toast(`Order #${order.order_number || order.id} placed!`, 'success');
            updateCartBadge(0);
            navigate('/orders');
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Place Order';
        }
    });
}

// ===== PAGE: ORDERS =====
async function initOrders() {
    const container = document.getElementById('orders-list');
    try {
        const res = await api.get(`${API.orders}/`);
        const orders = res.data || res || [];

        if (!Array.isArray(orders) || orders.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <p>No orders yet</p>
                    <a href="#/products" class="btn btn-primary" style="margin-top:1rem;">Start Shopping</a>
                </div>`;
            return;
        }

        container.innerHTML = `<div class="orders-grid">${orders.map(o => `
            <div class="order-card">
                <div class="order-header">
                    <span class="order-number">${esc(o.order_number || `Order #${o.id}`)}</span>
                    <span class="order-status status-${(o.status || 'pending').toLowerCase()}">${esc(o.status || 'pending')}</span>
                </div>
                <div class="order-details">
                    <span>Items: ${o.items ? o.items.length : '—'}</span>
                    <span class="order-total">Total: $${num(o.total)}</span>
                    <span>${o.created_at ? new Date(o.created_at).toLocaleDateString() : ''}</span>
                </div>
            </div>
        `).join('')}</div>`;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>${esc(err.message)}</p></div>`;
    }
}

// ===== PAGE: LOGIN =====
function initLogin() {
    if (api.getToken()) { navigate('/'); return; }
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btn-login');
        btn.disabled = true;
        btn.textContent = 'Signing in...';

        try {
            const form = e.target;
            const res = await api.post(`${API.auth}/login`, {
                email: form.email.value,
                password: form.password.value,
            });
            api.setTokens(res.access_token, res.refresh_token);

            // Fetch user profile
            try {
                const userRes = await api.get(`${API.users}/me`);
                api.setUser(userRes.data || userRes);
            } catch { /* will work without it */ }

            updateNavbar();
            fetchCartCount();
            toast('Welcome back!', 'success');
            navigate('/');
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });
}

// ===== PAGE: REGISTER =====
function initRegister() {
    if (api.getToken()) { navigate('/'); return; }
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btn-register');
        btn.disabled = true;
        btn.textContent = 'Creating account...';

        try {
            const form = e.target;
            await api.post(`${API.auth}/register`, {
                email: form.email.value,
                password: form.password.value,
                first_name: form.first_name.value,
                last_name: form.last_name.value,
                phone: form.phone.value || undefined,
            });
            toast('Account created! Please login.', 'success');
            navigate('/login');
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
    });
}

// ===== PAGE: PROFILE =====
async function initProfile() {
    const container = document.getElementById('profile-content');
    try {
        const res = await api.get(`${API.users}/me`);
        const u = res.data || res;
        api.setUser(u);

        container.innerHTML = `
            <div class="profile-card">
                <div class="profile-header">
                    <div class="profile-avatar">${(u.first_name?.[0] || 'U').toUpperCase()}</div>
                    <div>
                        <div class="profile-name">${esc(u.first_name || '')} ${esc(u.last_name || '')}</div>
                        <div class="profile-email">${esc(u.email)}</div>
                    </div>
                </div>
                <div class="profile-fields">
                    <div class="profile-field">
                        <label>Role</label>
                        <p>${esc(u.role || 'customer')}</p>
                    </div>
                    <div class="profile-field">
                        <label>Phone</label>
                        <p>${esc(u.phone || 'Not set')}</p>
                    </div>
                    <div class="profile-field">
                        <label>Email Verified</label>
                        <p>${u.is_verified ? '✅ Yes' : '❌ No'}</p>
                    </div>
                    <div class="profile-field">
                        <label>Member Since</label>
                        <p>${u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</p>
                    </div>
                </div>
            </div>
            <div style="margin-top:1.5rem; display:flex; gap:1rem;">
                <a href="#/orders" class="btn btn-glass">My Orders</a>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>${esc(err.message)}</p></div>`;
    }
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    // Mobile toggle
    document.getElementById('mobile-toggle').addEventListener('click', () => {
        document.getElementById('navbar').classList.toggle('mobile-open');
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', () => {
        api.clearTokens();
        updateNavbar();
        updateCartBadge(0);
        toast('Logged out', 'info');
        navigate('/');
    });

    // Init
    updateNavbar();
    fetchCartCount();
    window.addEventListener('hashchange', router);
    router();
});

// Make functions globally accessible for inline event handlers
window.navigate = navigate;
window.addToCart = addToCart;
window.updateCartItem = updateCartItem;
window.removeCartItem = removeCartItem;
window.currentPage = currentPage;
window.loadProducts = loadProducts;
window.toast = toast;
