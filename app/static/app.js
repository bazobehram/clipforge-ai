// ==========================================
// 0. VERSİYON & GÜNCELLEME TAKİBİ
// ==========================================
const APP_VERSION = '2.6.6';
const APP_BUILD_ID = '20260913_125500';

document.addEventListener('DOMContentLoaded', () => {
    // Versiyon ve Güncelleme Takibi
    initVersionTracking();

    // Auth Elemanları
    const loginModal = document.getElementById('login-modal');
    const loginForm = document.getElementById('login-form');
    const loginPassword = document.getElementById('login-password');
    const togglePwdBtn = document.getElementById('toggle-pwd-btn');
    const loginError = document.getElementById('login-error');
    const loginErrorText = document.getElementById('login-error-text');
    const logoutBtn = document.getElementById('logout-btn');

    // Analiz Formu Elemanları
    const analyzeForm = document.getElementById('analyze-form');
    const submitAnalyzeBtn = document.getElementById('submit-analyze-btn');
    const urlInput = document.getElementById('video-url');
    const pasteBtn = document.getElementById('paste-btn');
    const clearUrlBtn = document.getElementById('clear-url-btn');
    const verticalModeInput = document.getElementById('vertical-mode');
    const initialCountInput = document.getElementById('initial-count');

    // Kullanıcının ayarlarını hatırla (localStorage)
    const savedVerticalMode = localStorage.getItem('clipforge_vertical_mode');
    if (savedVerticalMode && verticalModeInput) {
        verticalModeInput.value = savedVerticalMode;
    }
    if (verticalModeInput) {
        verticalModeInput.addEventListener('change', () => {
            localStorage.setItem('clipforge_vertical_mode', verticalModeInput.value);
        });
    }

    const savedInitialCount = localStorage.getItem('clipforge_initial_count');
    if (savedInitialCount && initialCountInput) {
        initialCountInput.value = savedInitialCount;
    }
    if (initialCountInput) {
        initialCountInput.addEventListener('change', () => {
            localStorage.setItem('clipforge_initial_count', initialCountInput.value);
        });
    }

    // İlerleme Elemanları
    const progressContainer = document.getElementById('progress-container');
    const progressSpinner = document.getElementById('progress-spinner');
    const progressSuccessIcon = document.getElementById('progress-success-icon');
    const progressStatus = document.getElementById('progress-status');
    const progressPercent = document.getElementById('progress-percent');
    const progressBar = document.getElementById('progress-bar');
    const cancelAnalyzeBtn = document.getElementById('cancel-analyze-btn');

    // Proje Başlık Elemanları
    const projectHeader = document.getElementById('project-header');
    const projectThumb = document.getElementById('project-thumb');
    const projectThumbFallback = document.getElementById('project-thumb-fallback');
    const projectTitle = document.getElementById('project-title');
    const projectMeta = document.getElementById('project-meta');
    const scrollRenderedBtn = document.getElementById('scroll-rendered-btn');
    const renderedCountBadge = document.getElementById('rendered-count-badge');

    // Adaylar Bölümü
    const candidatesContainer = document.getElementById('candidates-container');
    const candidatesGrid = document.getElementById('candidates-grid');
    const candidatesCountBadge = document.getElementById('candidates-count-badge');
    const loadMoreCandidatesBtn = document.getElementById('load-more-candidates-btn');

    // Render Edilmiş Klipler Bölümü
    const renderedContainer = document.getElementById('rendered-container');
    const renderedGrid = document.getElementById('rendered-grid');
    const renderedTotalBadge = document.getElementById('rendered-total-badge');

    // Mobil & Sekme (Segmented Control) Elemanları
    const projectViewTabs = document.getElementById('project-view-tabs');
    const tabBtnCandidates = document.getElementById('tab-btn-candidates');
    const tabBtnRendered = document.getElementById('tab-btn-rendered');
    const mainBadgeCandidates = document.getElementById('main-badge-candidates');
    const mainBadgeRendered = document.getElementById('main-badge-rendered');
    const mobileBottomNav = document.getElementById('mobile-bottom-nav');
    const navBtnCandidates = document.getElementById('nav-btn-candidates');
    const navBtnRendered = document.getElementById('nav-btn-rendered');
    const bottomNavRenderedBadge = document.getElementById('bottom-nav-rendered-badge');

    // Geçmiş (History) Drawer Elemanları
    const openHistoryBtn = document.getElementById('open-history-btn');
    const closeHistoryBtn = document.getElementById('close-history-btn');
    const historyDrawer = document.getElementById('history-drawer');
    const historyList = document.getElementById('history-list');
    const historyBadge = document.getElementById('history-badge');

    // Aktif Durum (State)
    let currentProject = null;
    let pollInterval = null;
    let activeJobId = localStorage.getItem('clipforge_active_job_id') || null;
    let currentMainView = 'candidates'; // 'candidates' | 'rendered'

    // ==========================================
    // 0.05. ANA GÖRÜNÜM GEÇİŞLERİ (ADAYLAR vs HAZIR KLİPLER)
    // ==========================================
    window.switchMainView = function(view) {
        currentMainView = view;

        const trailerView = document.getElementById('trailer-studio-view');
        if (trailerView && !trailerView.classList.contains('hidden')) {
            window.switchStudioMode('shorts');
        }

        const navBtnTrailer = document.getElementById('nav-btn-trailer');
        if (navBtnTrailer) {
            navBtnTrailer.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95';
        }

        if (view === 'rendered') {
            if (candidatesContainer) candidatesContainer.classList.add('hidden');
            if (renderedContainer) renderedContainer.classList.remove('hidden');

            if (tabBtnCandidates) {
                tabBtnCandidates.className = 'py-2.5 px-3 rounded-xl font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all text-slate-400 hover:text-white';
            }
            if (tabBtnRendered) {
                tabBtnRendered.className = 'py-2.5 px-3 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-600/25';
            }
            if (navBtnCandidates) {
                navBtnCandidates.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95';
            }
            if (navBtnRendered) {
                navBtnRendered.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-emerald-400 font-bold transition-all active:scale-95 relative';
            }
        } else {
            if (candidatesContainer) candidatesContainer.classList.remove('hidden');
            if (renderedContainer) renderedContainer.classList.add('hidden');

            if (tabBtnCandidates) {
                tabBtnCandidates.className = 'py-2.5 px-3 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all bg-indigo-600 text-white shadow-md shadow-indigo-600/25';
            }
            if (tabBtnRendered) {
                tabBtnRendered.className = 'py-2.5 px-3 rounded-xl font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all text-slate-400 hover:text-white';
            }
            if (navBtnCandidates) {
                navBtnCandidates.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-indigo-400 font-bold transition-all active:scale-95';
            }
            if (navBtnRendered) {
                navBtnRendered.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95 relative';
            }
        }
    };

    window.jumpToRenderedClip = function(clipId) {
        window.switchMainView('rendered');
        setTimeout(() => {
            const card = document.getElementById('rendered-card-' + clipId);
            if (card) {
                const vid = card.querySelector('video');
                if (vid) {
                    try { vid.load(); } catch (e) {}
                }
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.classList.add('ring-4', 'ring-emerald-400/90', 'transition-all', 'duration-500');
                setTimeout(() => {
                    card.classList.remove('ring-4', 'ring-emerald-400/90');
                }, 2500);
            }
        }, 120);
    };

    window.jumpToCandidateClip = function(candId) {
        window.switchMainView('candidates');
        setTimeout(() => {
            const card = document.getElementById('cand-card-' + candId);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.classList.add('ring-4', 'ring-indigo-400/90', 'transition-all', 'duration-500');
                setTimeout(() => {
                    card.classList.remove('ring-4', 'ring-indigo-400/90');
                }, 2500);
            }
        }, 120);
    };

    // ==========================================
    // 0.06. TEKRARLAYAN İNDİRMEYİ ÖNLEME
    // ==========================================
    window.isClipDownloaded = function(clipId) {
        return localStorage.getItem('cf_dl_' + clipId) === '1';
    };

    window.markClipDownloaded = function(clipId) {
        try {
            localStorage.setItem('cf_dl_' + clipId, '1');
            const dlBtn = document.getElementById('mp4-dl-btn-' + clipId);
            if (dlBtn) {
                dlBtn.innerHTML = '<i class="fa-solid fa-circle-check text-sm text-emerald-400"></i> Tekrar İndir';
            }
        } catch (e) {}
    };

    // ==========================================
    // 0.1. SÜRÜM & ÖNBELLEK TAKİBİ FONKSİYONLARI
    // ==========================================
    function initVersionTracking() {
        const badge = document.getElementById('app-version-badge');
        const versionText = document.getElementById('version-text');
        const loginBadge = document.getElementById('login-version-badge');

        if (versionText) {
            versionText.textContent = `v${APP_VERSION}`;
        }
        if (badge) {
            badge.title = `ClipForge AI v${APP_VERSION} (Build: ${APP_BUILD_ID})\nSon sürümü kontrol etmek için tıklayın.`;
            badge.addEventListener('click', () => {
                showToast(`Sürüm kontrol ediliyor... (Mevcut: v${APP_VERSION})`, 'info');
                checkForNewVersion(true);
            });
        }
        if (loginBadge) {
            loginBadge.textContent = `v${APP_VERSION} • Build ${APP_BUILD_ID}`;
        }

        // Sayfa açıldıktan 2.5 saniye sonra sunucudan sürüm kontrolü yap
        setTimeout(() => {
            checkForNewVersion(false);
        }, 2500);
    }

    async function checkForNewVersion(manual = false) {
        try {
            const res = await fetch(`/api/version?_t=${Date.now()}`, { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();

            if (data.build_id && data.build_id !== APP_BUILD_ID) {
                // Döngü koruması: Aynı build için art arda reload döngüsüne girmeyi engelle
                const lastAttempted = sessionStorage.getItem('clipforge_reload_build_id');
                if (!manual && lastAttempted === data.build_id) {
                    console.warn('Update already attempted for build:', data.build_id);
                    return;
                }
                sessionStorage.setItem('clipforge_reload_build_id', data.build_id);

                // Sunucuda daha yeni bir build var! Önbellekleri temizle ve sayfayı yenile
                if ('caches' in window) {
                    try {
                        const keys = await caches.keys();
                        await Promise.all(keys.map(k => caches.delete(k)));
                    } catch (e) {}
                }
                if ('serviceWorker' in navigator) {
                    try {
                        const regs = await navigator.serviceWorker.getRegistrations();
                        for (let r of regs) { 
                            await r.unregister(); 
                        }
                    } catch (e) {}
                }
                showToast(`Yeni sürüm mevcut (v${data.version})! Sayfa güncelleniyor...`, 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else if (manual) {
                showToast(`Harika! En güncel sürümü kullanıyorsunuz: v${APP_VERSION} (${data.build_date})`, 'success');
            }
        } catch (err) {
            if (manual) {
                showToast(`Sunucuya erişilemedi: ${err.message}`, 'error');
            }
        }
    }

    // ==========================================
    // 1. AUTH / GİRİŞ YÖNETİMİ (Çift Katmanlı Kalıcı Oturum: Cookie + LocalStorage)
    // ==========================================
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    function setCookie(name, value, days = 365) {
        const d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/;SameSite=Lax`;
    }

    function deleteCookie(name) {
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;SameSite=Lax`;
    }

    function getToken() {
        let token = localStorage.getItem('clipforge_token') || '';
        if (!token) {
            token = getCookie('auth_token');
            if (token) {
                localStorage.setItem('clipforge_token', token);
            }
        } else {
            if (!getCookie('auth_token')) {
                setCookie('auth_token', token);
            }
        }
        return token;
    }

    function setToken(token) {
        localStorage.setItem('clipforge_token', token);
        setCookie('auth_token', token);
    }

    function clearToken() {
        localStorage.removeItem('clipforge_token');
        deleteCookie('auth_token');
    }

    async function fetchWithAuth(url, options = {}) {
        const token = getToken();
        options.headers = options.headers || {};
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }
        options.credentials = 'same-origin';
        const res = await fetch(url, options);
        if (res.status === 401) {
            clearToken();
            showLoginModal();
            throw new Error('Oturum süresi doldu veya yetkisiz erişim.');
        }
        return res;
    }

    async function checkAuth() {
        const token = getToken();
        if (!token) {
            showLoginModal();
            return false;
        }
        try {
            const res = await fetchWithAuth('/api/auth/verify');
            if (res.ok) {
                hideLoginModal();
                loadHistory();
                restoreActiveJobIfNeeded();
                return true;
            }
        } catch (e) {
            if (e.message && e.message.includes('yetkisiz')) {
                showLoginModal();
            }
            return false;
        }
        return false;
    }

    function showLoginModal() {
        loginModal.classList.remove('hidden');
        loginPassword.value = '';
        loginError.classList.add('hidden');
        loginPassword.focus();
    }

    function hideLoginModal() {
        loginModal.classList.add('hidden');
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const pwd = loginPassword.value.trim();
        if (!pwd) return;

        loginError.classList.add('hidden');
        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });
            const data = await res.json();
            if (!res.ok) {
                loginErrorText.textContent = data.detail || 'Giriş başarısız.';
                loginError.classList.remove('hidden');
                return;
            }
            setToken(data.token);
            hideLoginModal();
            showToast('Giriş başarılı!', 'success');
            loadHistory();
            restoreActiveJobIfNeeded();
        } catch (err) {
            loginErrorText.textContent = 'Bağlantı hatası: ' + err.message;
            loginError.classList.remove('hidden');
        }
    });

    togglePwdBtn.addEventListener('click', () => {
        const type = loginPassword.type === 'password' ? 'text' : 'password';
        loginPassword.type = type;
        togglePwdBtn.innerHTML = type === 'password' ? '<i class="fa-regular fa-eye text-sm"></i>' : '<i class="fa-regular fa-eye-slash text-sm"></i>';
    });

    logoutBtn.addEventListener('click', () => {
        clearToken();
        showLoginModal();
        showToast('Çıkış yapıldı.', 'info');
    });

    // ==========================================
    // 2. PANODAN YAPIŞTIRMA & INPUT
    // ==========================================
    pasteBtn.addEventListener('click', async () => {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const text = await navigator.clipboard.readText();
                if (text && (text.includes('youtube.com') || text.includes('youtu.be'))) {
                    urlInput.value = text.trim();
                    clearUrlBtn.classList.remove('hidden');
                    showToast('YouTube linki panodan yapıştırıldı!', 'success');
                } else if (text) {
                    urlInput.value = text.trim();
                    clearUrlBtn.classList.remove('hidden');
                    showToast('Metin yapıştırıldı.', 'info');
                } else {
                    showToast('Pano boş.', 'info');
                }
            } else {
                urlInput.focus();
                showToast('Lütfen linki doğrudan kutuya yapıştırın.', 'info');
            }
        } catch (err) {
            urlInput.focus();
            showToast('Panoya erişim izni verilmedi, elle yapıştırabilirsiniz.', 'info');
        }
    });

    urlInput.addEventListener('input', () => {
        if (urlInput.value.trim().length > 0) {
            clearUrlBtn.classList.remove('hidden');
        } else {
            clearUrlBtn.classList.add('hidden');
        }
    });

    clearUrlBtn.addEventListener('click', () => {
        urlInput.value = '';
        clearUrlBtn.classList.add('hidden');
        urlInput.focus();
    });

    // ==========================================
    // 3. AŞAMA 1: YOUTUBE ANALİZİ (ADAY ÇIKARMA)
    // ==========================================
    analyzeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        submitAnalyzeBtn.disabled = true;
        submitAnalyzeBtn.classList.add('opacity-60', 'cursor-not-allowed');

        progressContainer.classList.remove('hidden');
        progressSpinner.classList.remove('hidden');
        progressSuccessIcon.classList.add('hidden');

        candidatesContainer.classList.add('hidden');
        renderedContainer.classList.add('hidden');
        projectHeader.classList.add('hidden');

        updateProgress(5, 'İşlem başlatılıyor ve sunucuya iletiliyor...');
        setActiveStep('step-dl');

        try {
            const res = await fetchWithAuth('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    vertical_mode: verticalModeInput.value,
                    count: parseInt(initialCountInput.value)
                })
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Analiz isteği gönderilemedi.');
            }

            const data = await res.json();

            // Eğer video daha önce analiz edilmişse anında geçmişten yükle
            if (data.from_history && data.project) {
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
                loadProjectFromData(data.job_id, data.project);
                loadHistory();
                showToast(data.message || 'Bu video daha önce analiz edilmiş, anında yüklendi!', 'success');
                return;
            }

            activeJobId = data.job_id;
            localStorage.setItem('clipforge_active_job_id', activeJobId);

            if (data.reused) {
                showToast('Bu video için devam eden analize bağlanıldı.', 'info');
            }

            startAnalyzePolling(data.job_id);

        } catch (err) {
            showToast('Hata: ' + err.message, 'error');
            resetAnalyzeBtn();
            progressContainer.classList.add('hidden');
        }
    });

    let analyzeElapsedSec = 0;
    let analyzeTimerInterval = null;

    function startAnalyzeTimer() {
        if (analyzeTimerInterval) clearInterval(analyzeTimerInterval);
        analyzeElapsedSec = 0;
        const timerEl = document.getElementById('progress-timer');
        if (timerEl) timerEl.textContent = '⏱️ 0s';

        analyzeTimerInterval = setInterval(() => {
            analyzeElapsedSec++;
            const m = Math.floor(analyzeElapsedSec / 60);
            const s = analyzeElapsedSec % 60;
            if (timerEl) {
                timerEl.textContent = m > 0 ? `⏱️ ${m}dk ${s}s` : `⏱️ ${s}s`;
            }
        }, 1000);
    }

    function stopAnalyzeTimer() {
        if (analyzeTimerInterval) {
            clearInterval(analyzeTimerInterval);
            analyzeTimerInterval = null;
        }
    }

    function startAnalyzePolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);
        startAnalyzeTimer();

        pollInterval = setInterval(async () => {
            try {
                const res = await fetchWithAuth(`/api/analyze/${jobId}`);
                if (!res.ok) throw new Error('Durum sorgulanamadı.');
                const job = await res.json();

                updateProgress(job.progress, job.message, job.sub_status);

                if (job.status === 'downloading') setActiveStep('step-dl');
                else if (job.status === 'transcribing') setActiveStep('step-tr');
                else if (job.status === 'scoring') setActiveStep('step-sc');

                if (job.status === 'completed') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    stopAnalyzeTimer();
                    localStorage.removeItem('clipforge_active_job_id');
                    activeJobId = null;

                    // SPINNER GİZLE, CHECKMARK GÖSTER
                    progressSpinner.classList.add('hidden');
                    progressSuccessIcon.classList.remove('hidden');
                    updateProgress(100, `${job.candidates ? job.candidates.length : 0} adet viral aday bölüm hazırlandı!`);

                    resetAnalyzeBtn();
                    loadProjectFromData(jobId, job);
                    loadHistory();
                    showToast('Viral aday bölümler hazır!', 'success');
                } else if (job.status === 'failed') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    stopAnalyzeTimer();
                    localStorage.removeItem('clipforge_active_job_id');
                    activeJobId = null;

                    resetAnalyzeBtn();
                    progressSpinner.classList.add('hidden');
                    showToast('Hata: ' + (job.error || 'İşlem tamamlanamadı.'), 'error');
                } else if (job.status === 'interrupted') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    stopAnalyzeTimer();
                    localStorage.removeItem('clipforge_active_job_id');
                    activeJobId = null;

                    resetAnalyzeBtn();
                    progressContainer.classList.add('hidden');
                    showToast('İşlem sunucu güncellemesi nedeniyle kesintiye uğradı. "Geçmiş" menüsünden tek tıkla tekrar başlatabilirsiniz.', 'warning');
                } else if (job.status === 'cancelled') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    stopAnalyzeTimer();
                    localStorage.removeItem('clipforge_active_job_id');
                    activeJobId = null;

                    resetAnalyzeBtn();
                    progressContainer.classList.add('hidden');
                    showToast('Analiz işlemi iptal edildi.', 'info');
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 1500);
    }

    // İptal Butonu Dinleyicisi
    if (cancelAnalyzeBtn) {
        cancelAnalyzeBtn.addEventListener('click', async () => {
            const jid = activeJobId || localStorage.getItem('clipforge_active_job_id');
            if (!jid) {
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
                return;
            }

            if (!confirm('Devam eden analiz işlemini iptal etmek istediğinize emin misiniz?')) {
                return;
            }

            const origHtml = cancelAnalyzeBtn.innerHTML;
            cancelAnalyzeBtn.disabled = true;
            cancelAnalyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i> İptal...';

            try {
                await fetchWithAuth(`/api/analyze/${jid}/cancel`, { method: 'POST' });
            } catch (e) {
                console.warn('Cancel error:', e);
            } finally {
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
                localStorage.removeItem('clipforge_active_job_id');
                activeJobId = null;
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
                cancelAnalyzeBtn.disabled = false;
                cancelAnalyzeBtn.innerHTML = origHtml;
                showToast('Analiz işlemi başarıyla iptal edildi.', 'info');
            }
        });
    }

    // Sayfa Yenilendiğinde veya Telefon Kilidi Açıldığında Aktif İşi Geri Yükle
    async function restoreActiveJobIfNeeded() {
        const savedJobId = localStorage.getItem('clipforge_active_job_id');
        let targetJobId = savedJobId;

        if (!targetJobId) {
            // Sunucuda halen aktif çalışan bir iş var mı kontrol et
            try {
                const res = await fetchWithAuth('/api/analyze/active');
                if (res.ok) {
                    const data = await res.json();
                    if (data.active && data.job) {
                        targetJobId = data.job.job_id;
                        localStorage.setItem('clipforge_active_job_id', targetJobId);
                    }
                }
            } catch (e) {}
        }

        if (!targetJobId) return;

        try {
            const res = await fetchWithAuth(`/api/analyze/${targetJobId}`);
            if (!res.ok) {
                localStorage.removeItem('clipforge_active_job_id');
                return;
            }
            const job = await res.json();

            if (job.status === 'completed') {
                localStorage.removeItem('clipforge_active_job_id');
                activeJobId = null;
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
                loadProjectFromData(targetJobId, job);
            } else if (job.status === 'interrupted') {
                localStorage.removeItem('clipforge_active_job_id');
                activeJobId = null;
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
                showToast('Önceki işlem sunucu güncellemesi nedeniyle kesintiye uğradı. "Geçmiş & İşlemler" menüsünden tekrar başlatabilirsiniz.', 'warning');
            } else if (job.status === 'failed' || job.status === 'cancelled') {
                localStorage.removeItem('clipforge_active_job_id');
                activeJobId = null;
                resetAnalyzeBtn();
                progressContainer.classList.add('hidden');
            } else {
                // Halen devam eden analiz (%15, %45, %75 vs.)
                activeJobId = targetJobId;
                submitAnalyzeBtn.disabled = true;
                submitAnalyzeBtn.classList.add('opacity-60', 'cursor-not-allowed');

                progressContainer.classList.remove('hidden');
                progressSpinner.classList.remove('hidden');
                progressSuccessIcon.classList.add('hidden');
                candidatesContainer.classList.add('hidden');
                renderedContainer.classList.add('hidden');
                projectHeader.classList.add('hidden');

                updateProgress(job.progress || 10, job.message || 'İşleme devam ediliyor...');
                if (job.status === 'downloading') setActiveStep('step-dl');
                else if (job.status === 'transcribing') setActiveStep('step-tr');
                else if (job.status === 'scoring') setActiveStep('step-sc');

                startAnalyzePolling(targetJobId);
                showToast('Devam eden analiz süreci geri yüklendi.', 'info');
            }
        } catch (e) {
            console.warn('Failed to restore active job:', e);
        }
    }

    // Telefon uyandığında veya sekmeye geri dönüldüğünde hemen durumu tazele
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && (activeJobId || localStorage.getItem('clipforge_active_job_id'))) {
            restoreActiveJobIfNeeded();
        }
    });

    function updateProgress(percent, message, subStatus = null) {
        progressBar.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        if (message) progressStatus.textContent = message;

        const subBox = document.getElementById('progress-substatus-box');
        const subEl = document.getElementById('progress-substatus');
        if (subBox && subEl) {
            if (subStatus && subStatus.trim().length > 0) {
                subBox.classList.remove('hidden');
                subEl.textContent = `"${subStatus.trim()}"`;
            } else if (percent >= 100) {
                subBox.classList.add('hidden');
            }
        }
    }

    function setActiveStep(activeId) {
        ['step-dl', 'step-tr', 'step-sc'].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            if (id === activeId) {
                el.className = 'py-1 rounded bg-indigo-600/30 border border-indigo-500 text-indigo-200 font-bold';
            } else {
                el.className = 'py-1 rounded bg-slate-950 border border-slate-850 text-slate-500';
            }
        });
    }

    function resetAnalyzeBtn() {
        submitAnalyzeBtn.disabled = false;
        submitAnalyzeBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }

    // ==========================================
    // 4. PROJE YÜKLEME VE GÖSTERİMİ
    // ==========================================
    async function checkProjectTrailer(projectId) {
        const banner = document.getElementById('project-trailer-banner');
        const bannerMeta = document.getElementById('project-trailer-banner-meta');
        const bannerBtn = document.getElementById('project-trailer-banner-btn');
        if (!banner) return;

        try {
            const res = await fetchWithAuth(`/api/projects/${projectId}/trailer`);
            if (res.ok) {
                const data = await res.json();
                if (data.exists && data.trailer) {
                    const t = data.trailer;
                    if (bannerMeta) {
                        bannerMeta.textContent = `${t.aspect_ratio || '9:16'} • ${(t.scenes || []).length} Bölüm • ${t.duration ? Math.round(t.duration) + 's' : ''}`;
                    }
                    if (bannerBtn) {
                        bannerBtn.onclick = () => window.openTrailerById(t.trailer_id);
                    }
                    banner.classList.remove('hidden');
                    return;
                }
            }
        } catch (e) {
            console.warn('checkProjectTrailer error:', e);
        }
        banner.classList.add('hidden');
    }

    function loadProjectFromData(projectId, data) {
        currentProject = {
            project_id: projectId,
            youtube_url: data.youtube_url || data.url || (urlInput ? urlInput.value.trim() : '') || '',
            title: data.video_title || data.title || 'YouTube Video',
            duration: data.duration || 0,
            thumbnail: data.thumbnail || '',
            candidates: data.candidates || [],
            rendered_clips: data.rendered_clips || []
        };

        // Proje Başlık Bilgisi
        if (projectHeader) projectHeader.classList.remove('hidden');
        if (projectTitle) projectTitle.textContent = currentProject.title;
        if (projectMeta) projectMeta.textContent = `${Math.round(currentProject.duration)} sn • Toplam ${currentProject.candidates.length} Aday • ${currentProject.rendered_clips.length} Klip Render Edildi`;

        if (currentProject.thumbnail) {
            if (projectThumb) {
                projectThumb.src = currentProject.thumbnail;
                projectThumb.classList.remove('hidden');
            }
            if (projectThumbFallback) projectThumbFallback.classList.add('hidden');
        } else {
            if (projectThumb) projectThumb.classList.add('hidden');
            if (projectThumbFallback) projectThumbFallback.classList.remove('hidden');
        }

        // Projeye ait akıllı fragman kontrolü yap ve banner'ı göster
        checkProjectTrailer(projectId);

        renderCandidates(currentProject.candidates);
        renderFinishedClips(currentProject.rendered_clips);

        // Segmented Control ve Mobil Alt Barı Aç
        if (projectViewTabs) projectViewTabs.classList.remove('hidden');
        if (mobileBottomNav) mobileBottomNav.classList.remove('hidden');

        // Rozetleri Güncelle
        if (mainBadgeCandidates) mainBadgeCandidates.textContent = currentProject.candidates.length;
        if (mainBadgeRendered) mainBadgeRendered.textContent = currentProject.rendered_clips.length;
        if (bottomNavRenderedBadge) {
            if (currentProject.rendered_clips.length > 0) {
                bottomNavRenderedBadge.classList.remove('hidden');
            } else {
                bottomNavRenderedBadge.classList.add('hidden');
            }
        }

        // Eğer hazır üretilmiş klip varsa doğrudan Hazır Klipler sekmesini aç, yoksa Adaylar sekmesini aç
        const defaultView = (currentProject.rendered_clips && currentProject.rendered_clips.length > 0) ? 'rendered' : 'candidates';
        window.switchMainView(defaultView);
    }

    // ==========================================
    // 4.9. ADAY KATEGORİ, FİLTRE VE SÜRE ÖLÇEĞİ FONKSİYONLARI
    // ==========================================
    let activeCandidateTab = 'all';

    function getCandidateCategory(cand) {
        if (cand.source_type) return cand.source_type;
        if (cand.id && cand.id.includes('_custom_')) return 'custom';
        if (cand.id && cand.id.includes('_search_')) return 'search';
        return 'ai';
    }

    function formatPlatformName(p) {
        if (!p) return '';
        const map = {
            'instagram': 'Instagram',
            'tiktok': 'TikTok',
            'youtube': 'Shorts',
            'twitter': 'X',
            'bluesky': 'Bluesky',
            'native': 'Mobil',
            'manual': 'İşaretlendi'
        };
        return map[p] || p;
    }

    window.setCandidateScale = function(candId, scale) {
        if (!currentProject) return;
        const cand = (currentProject.candidates || []).find(c => String(c.id) === String(candId));
        if (!cand) return;

        if (cand.orig_start_time === undefined) {
            cand.orig_start_time = cand.start_time;
            cand.orig_end_time = cand.end_time;
            cand.orig_duration = cand.duration || (cand.end_time - cand.start_time);
        }

        const videoDur = (currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;
        let newStart = cand.orig_start_time;
        let newEnd = cand.orig_end_time;

        if (scale === 'short') {
            newStart = cand.orig_start_time;
            newEnd = cand.orig_end_time;
        } else if (scale === 'medium') {
            newStart = Math.max(0, cand.orig_start_time - 3);
            newEnd = Math.min(videoDur, cand.orig_end_time + 7);
        } else if (scale === 'long') {
            newStart = Math.max(0, cand.orig_start_time - 5);
            newEnd = Math.min(videoDur, cand.orig_end_time + 15);
        }

        cand.start_time = Math.round(newStart * 10) / 10;
        cand.end_time = Math.round(newEnd * 10) / 10;
        cand.duration = Math.round((cand.end_time - cand.start_time) * 10) / 10;
        cand.active_scale = scale;

        updateCandidateDurationUI(cand);
    };

    window.adjustCandidateDuration = function(candId, deltaSec) {
        if (!currentProject) return;
        const cand = (currentProject.candidates || []).find(c => String(c.id) === String(candId));
        if (!cand) return;

        if (cand.orig_start_time === undefined) {
            cand.orig_start_time = cand.start_time;
            cand.orig_end_time = cand.end_time;
            cand.orig_duration = cand.duration || (cand.end_time - cand.start_time);
        }

        const videoDur = (currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;
        let newEnd = cand.end_time + deltaSec;
        if (newEnd <= cand.start_time + 5) {
            newEnd = cand.start_time + 5;
        }
        if (newEnd > videoDur) {
            newEnd = videoDur;
        }

        cand.end_time = Math.round(newEnd * 10) / 10;
        cand.duration = Math.round((cand.end_time - cand.start_time) * 10) / 10;
        cand.active_scale = 'custom';

        updateCandidateDurationUI(cand);
    };

    window.resetCandidateDuration = function(candId) {
        if (!currentProject) return;
        const cand = (currentProject.candidates || []).find(c => String(c.id) === String(candId));
        if (!cand || cand.orig_start_time === undefined) return;

        cand.start_time = cand.orig_start_time;
        cand.end_time = cand.orig_end_time;
        cand.duration = cand.orig_duration;
        cand.active_scale = 'short';

        updateCandidateDurationUI(cand);
    };

    function updateCandidateDurationUI(cand) {
        const dispEl = document.getElementById(`cand-duration-display-${cand.id}`);
        if (dispEl) {
            dispEl.textContent = `${formatSec(cand.start_time)} - ${formatSec(cand.end_time)} (${Math.round(cand.duration)}s)`;
        }
        const clockEl = document.getElementById(`cand-clock-${cand.id}`);
        if (clockEl) {
            clockEl.innerHTML = `<i class="fa-regular fa-clock"></i> [${formatSec(cand.start_time)} - ${formatSec(cand.end_time)}] • ${Math.round(cand.duration)}s`;
        }

        ['short', 'medium', 'long'].forEach(sc => {
            const btn = document.getElementById(`scale-btn-${sc}-${cand.id}`);
            if (btn) {
                if (cand.active_scale === sc) {
                    btn.className = 'scale-btn py-1.5 px-1 rounded-lg border text-center font-bold transition-all bg-indigo-600/30 border-indigo-500 text-indigo-200';
                } else {
                    btn.className = 'scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200';
                }
            }
        });
    }

    // ==========================================
    // 4.95. RENDER EDİLMİŞ KLİP İÇİN SÜRE ÖLÇEĞİ & DOĞRUDAN YENİDEN RENDER
    // ==========================================
    window.setRenderedClipScale = function(clipId, scale) {
        if (!currentProject) return;
        let cand = (currentProject.candidates || []).find(c => String(c.id) === String(clipId));
        let clip = (currentProject.rendered_clips || []).find(c => String(c.id) === String(clipId));
        if (!cand && clip) {
            cand = {
                id: clip.id,
                start_time: clip.start_time,
                end_time: clip.end_time,
                duration: clip.duration,
                title: clip.title,
                description: clip.description,
                hashtags: clip.hashtags,
                score: clip.score,
                is_rendered: true
            };
            currentProject.candidates.push(cand);
        }
        if (!cand) return;

        if (cand.orig_start_time === undefined) {
            cand.orig_start_time = cand.start_time;
            cand.orig_end_time = cand.end_time;
            cand.orig_duration = cand.duration || (cand.end_time - cand.start_time);
        }

        const videoDur = (currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;
        let newStart = cand.orig_start_time;
        let newEnd = cand.orig_end_time;

        if (scale === 'short') {
            newStart = cand.orig_start_time;
            newEnd = cand.orig_end_time;
        } else if (scale === 'medium') {
            newStart = Math.max(0, cand.orig_start_time - 3);
            newEnd = Math.min(videoDur, cand.orig_end_time + 7);
        } else if (scale === 'long') {
            newStart = Math.max(0, cand.orig_start_time - 5);
            newEnd = Math.min(videoDur, cand.orig_end_time + 15);
        }

        cand.start_time = Math.round(newStart * 10) / 10;
        cand.end_time = Math.round(newEnd * 10) / 10;
        cand.duration = Math.round((cand.end_time - cand.start_time) * 10) / 10;
        cand.active_scale = scale;

        updateRenderedDurationUI(clipId, cand);
    };

    window.adjustRenderedClipDuration = function(clipId, deltaSec) {
        if (!currentProject) return;
        let cand = (currentProject.candidates || []).find(c => String(c.id) === String(clipId));
        let clip = (currentProject.rendered_clips || []).find(c => String(c.id) === String(clipId));
        if (!cand && clip) {
            cand = {
                id: clip.id,
                start_time: clip.start_time,
                end_time: clip.end_time,
                duration: clip.duration,
                title: clip.title,
                description: clip.description,
                hashtags: clip.hashtags,
                score: clip.score,
                is_rendered: true
            };
            currentProject.candidates.push(cand);
        }
        if (!cand) return;

        if (cand.orig_start_time === undefined) {
            cand.orig_start_time = cand.start_time;
            cand.orig_end_time = cand.end_time;
            cand.orig_duration = cand.duration || (cand.end_time - cand.start_time);
        }

        const videoDur = (currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;
        let newEnd = cand.end_time + deltaSec;
        if (newEnd <= cand.start_time + 5) {
            newEnd = cand.start_time + 5;
        }
        if (newEnd > videoDur) {
            newEnd = videoDur;
        }

        cand.end_time = Math.round(newEnd * 10) / 10;
        cand.duration = Math.round((cand.end_time - cand.start_time) * 10) / 10;
        cand.active_scale = 'custom';

        updateRenderedDurationUI(clipId, cand);
    };

    function updateRenderedDurationUI(clipId, cand) {
        const dispEl = document.getElementById(`rendered-duration-display-${clipId}`);
        if (dispEl) {
            dispEl.textContent = `${formatSec(cand.start_time)} - ${formatSec(cand.end_time)} (${Math.round(cand.duration)}s)`;
        }
        const btn = document.getElementById(`rendered-rerender-btn-${clipId}`);
        if (btn) {
            btn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> <span>${Math.round(cand.duration)}s Yeniden Render Et</span>`;
        }

        ['short', 'medium', 'long'].forEach(sc => {
            const scBtn = document.getElementById(`rendered-scale-${sc}-${clipId}`);
            if (scBtn) {
                if (cand.active_scale === sc) {
                    scBtn.className = 'scale-btn py-1.5 px-1 rounded-lg border text-center font-bold transition-all bg-indigo-600/30 border-indigo-500 text-indigo-200';
                } else {
                    scBtn.className = 'scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200';
                }
            }
        });
    }

    window.reRenderFinishedClip = async function(clipId, btn) {
        // Düzenlenen metinleri varsa adayın girdi alanlarına kopyala
        const finalTitle = document.getElementById(`final-title-${clipId}`);
        const finalDesc = document.getElementById(`final-desc-${clipId}`);
        const finalTags = document.getElementById(`final-tags-${clipId}`);
        const candTitle = document.getElementById(`cand-title-${clipId}`);
        const candDesc = document.getElementById(`cand-desc-${clipId}`);
        const candTags = document.getElementById(`cand-tags-${clipId}`);

        if (finalTitle && candTitle) candTitle.value = finalTitle.value;
        if (finalDesc && candDesc) candDesc.value = finalDesc.value;
        if (finalTags && candTags) candTags.value = finalTags.value;

        // Render işlemini başlat
        await window.renderCandidateClip(clipId, btn);
    };

    function updateCandidateFilterCounts(candidates) {
        const total = candidates.length;
        const aiCount = candidates.filter(c => getCandidateCategory(c) === 'ai').length;
        const searchCount = candidates.filter(c => getCandidateCategory(c) === 'search').length;
        const customCount = candidates.filter(c => getCandidateCategory(c) === 'custom').length;

        const elAll = document.getElementById('tab-count-all');
        const elAi = document.getElementById('tab-count-ai');
        const elSearch = document.getElementById('tab-count-search');
        const elCustom = document.getElementById('tab-count-custom');

        if (elAll) elAll.textContent = total;
        if (elAi) elAi.textContent = aiCount;
        if (elSearch) elSearch.textContent = searchCount;
        if (elCustom) elCustom.textContent = customCount;

        const tabBtns = document.querySelectorAll('.candidate-filter-btn');
        tabBtns.forEach(btn => {
            const filter = btn.getAttribute('data-filter');
            if (filter === activeCandidateTab) {
                btn.className = 'candidate-filter-btn active-tab bg-indigo-600 text-white font-semibold px-3 py-1.5 rounded-xl border border-indigo-500 flex items-center gap-1.5 transition-all shadow-sm shrink-0';
            } else {
                btn.className = 'candidate-filter-btn bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white font-medium px-3 py-1.5 rounded-xl border border-slate-800 flex items-center gap-1.5 transition-all shrink-0';
            }
        });
    }

    // ==========================================
    // 5. ADAY KLİPLERİN LİSTELENMESİ (STAGE 1 UI)
    // ==========================================
    window.switchCandidateTab = function(tab) {
        activeCandidateTab = tab;
        if (currentProject && currentProject.candidates) {
            renderCandidates(currentProject.candidates);
        }
    };

    function renderCandidates(candidates) {
        candidatesContainer.classList.remove('hidden');
        candidatesCountBadge.textContent = `${candidates.length} Aday`;
        updateCandidateFilterCounts(candidates);

        candidatesGrid.innerHTML = '';

        const filtered = activeCandidateTab === 'all'
            ? candidates
            : candidates.filter(c => getCandidateCategory(c) === activeCandidateTab);

        if (candidates.length === 0) {
            const emptyEl = document.createElement('div');
            emptyEl.className = 'col-span-full bg-slate-900/60 border border-purple-500/30 rounded-2xl p-8 text-center space-y-3';
            emptyEl.innerHTML = `
                <div class="w-12 h-12 rounded-2xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center mx-auto text-purple-400">
                    <i class="fa-solid fa-film text-xl"></i>
                </div>
                <h4 class="text-sm sm:text-base font-bold text-white">Bu Projenin Akıllı Fragmanı / Özeti Hazır!</h4>
                <p class="text-xs text-slate-400 max-w-md mx-auto">Bu video için yapay zeka ile kilit anlar seçilip sinematik bir fragman oluşturuldu. Dilerseniz hemen izleyebilir ve doğrudan telefonda paylaşabilirsiniz.</p>
                <div class="flex items-center justify-center gap-2 pt-2">
                    <button type="button" onclick="if (currentProject) checkAndOpenProjectTrailer(currentProject.project_id)" 
                        class="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold px-4 py-2.5 rounded-xl text-xs sm:text-sm flex items-center gap-2 shadow-lg shadow-purple-600/30 active:scale-95 transition-all cursor-pointer">
                        <i class="fa-solid fa-play"></i> <span>Fragmanı Hemen İzle & Paylaş</span>
                    </button>
                </div>
            `;
            candidatesGrid.appendChild(emptyEl);
            return;
        }

        if (filtered.length === 0) {
            const emptyEl = document.createElement('div');
            emptyEl.className = 'col-span-full bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-3';
            const catName = activeCandidateTab === 'ai' ? 'AI viral aday' : (activeCandidateTab === 'search' ? 'konu araması' : 'özel kesit');
            emptyEl.innerHTML = `
                <i class="fa-solid fa-filter text-slate-600 text-2xl"></i>
                <p class="text-sm text-slate-400">Bu sekmede (${catName}) henüz klip bulunmuyor.</p>
                <button type="button" onclick="window.switchCandidateTab('all')" 
                    class="text-xs bg-slate-800 hover:bg-slate-750 text-indigo-300 px-3 py-1.5 rounded-xl border border-slate-700 transition-colors">
                    Tüm Klipleri Göster
                </button>
            `;
            candidatesGrid.appendChild(emptyEl);
            return;
        }

        const videoDur = (currentProject && currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;

        filtered.forEach((cand, idx) => {
            const card = document.createElement('div');
            const cat = getCandidateCategory(cand);
            const borderClass = cat === 'search' ? 'border-purple-500/60 shadow-purple-500/10 ring-1 ring-purple-500/30' :
                               (cat === 'custom' ? 'border-teal-500/60 shadow-teal-500/10 ring-1 ring-teal-500/30' : 'border-slate-800');
            card.className = `bg-slate-900 border ${borderClass} rounded-2xl p-4 sm:p-5 shadow-lg flex flex-col justify-between space-y-4 transition-all hover:border-slate-700`;
            card.id = `cand-card-${cand.id}`;

            const scoreBadge = cand.score >= 90 ? 'text-emerald-300 border-emerald-500/40 bg-emerald-500/15' :
                               cand.score >= 80 ? 'text-indigo-300 border-indigo-500/40 bg-indigo-500/15' :
                               'text-amber-300 border-amber-500/40 bg-amber-500/15';

            let typeBadge = '';
            if (cat === 'custom') {
                typeBadge = `<span class="text-xs font-bold px-2.5 py-0.5 rounded-full border border-teal-500/40 bg-teal-500/20 text-teal-300 flex items-center gap-1"><i class="fa-solid fa-scissors text-xs"></i> Özel Kesit</span>`;
            } else if (cat === 'search') {
                const qText = cand.source_query ? ` "${escapeHtml(cand.source_query)}"` : '';
                typeBadge = `<span class="text-xs font-bold px-2.5 py-0.5 rounded-full border border-purple-500/40 bg-purple-500/20 text-purple-300 flex items-center gap-1"><i class="fa-solid fa-wand-magic-sparkles text-yellow-300 text-xs"></i> Konu Kesiti${qText}</span>`;
            } else {
                typeBadge = `<span class="text-xs font-medium px-2 py-0.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 flex items-center gap-1"><i class="fa-solid fa-robot text-xs"></i> AI Viral</span>`;
            }

            const matchingClip = (currentProject && currentProject.rendered_clips) ? currentProject.rendered_clips.find(c => String(c.id) === String(cand.id)) : null;
            const isRendered = cand.is_rendered || !!matchingClip;
            const sharedPlatforms = (matchingClip && matchingClip.shared_platforms) ? matchingClip.shared_platforms : (cand.shared_platforms || []);
            const normShared = sharedPlatforms.map(p => p === 'x' ? 'twitter' : p);
            const sharedCount = ['instagram', 'tiktok', 'youtube', 'twitter', 'bluesky'].filter(p => normShared.includes(p)).length;
            const missingCount = 5 - sharedCount;
            const isShared = (matchingClip && matchingClip.is_shared) || cand.is_shared || sharedCount > 0;

            let renderedStatusBadge = '';
            if (isRendered) {
                renderedStatusBadge += `<span class="text-xs font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 flex items-center gap-1">
                     <i class="fa-solid fa-circle-check"></i> Render Edildi
                   </span>`;
            }
            if (isShared) {
                if (sharedCount > 0) {
                    const badgeClass = sharedCount === 5 
                        ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300' 
                        : 'border-indigo-500/40 bg-indigo-500/20 text-indigo-300';
                    renderedStatusBadge += `<span class="text-xs font-bold px-2.5 py-0.5 rounded-full border ${badgeClass} flex items-center gap-1">
                         <i class="fa-solid fa-share-nodes text-indigo-400"></i> ${sharedCount}/5 Paylaşıldı${missingCount > 0 ? ` (${missingCount} Eksik)` : ''}
                       </span>`;
                } else {
                    renderedStatusBadge += `<span class="text-xs font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/40 bg-emerald-500/20 text-emerald-300 flex items-center gap-1">
                         <i class="fa-solid fa-share-nodes text-emerald-400"></i> Paylaşıldı
                       </span>`;
                }
            }
            if (!isRendered) {
                renderedStatusBadge += `<span class="text-xs font-medium px-2.5 py-0.5 rounded-full border border-slate-700 bg-slate-800 text-slate-300">
                     Aday #${idx + 1}
                   </span>`;
            }

            if (cand.orig_start_time === undefined) {
                cand.orig_start_time = cand.start_time;
                cand.orig_end_time = cand.end_time;
                cand.orig_duration = cand.duration || (cand.end_time - cand.start_time);
            }
            const origDur = Math.round(cand.orig_duration || 30);
            const activeScale = cand.active_scale || 'short';
            const thumbUrl = cand.thumbnail_url || (currentProject ? `/api/thumbnails/${currentProject.project_id}/${cand.id}.jpg` : '');

            card.innerHTML = `
                <div class="space-y-3.5">
                    <!-- Üst Video Kesiti Önizleme (Thumbnail) & Hızlı Aksiyon -->
                    <div class="relative w-full aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-800/80 group">
                        ${thumbUrl ? `
                        <img src="${thumbUrl}" alt="${escapeHtml(cand.title)}" loading="lazy"
                            onerror="this.style.display='none'; this.nextElementSibling.classList.remove('hidden');"
                            class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
                        <div class="hidden absolute inset-0 flex items-center justify-center bg-slate-950 text-slate-600">
                            <i class="fa-solid fa-film text-2xl"></i>
                        </div>
                        ` : `
                        <div class="absolute inset-0 flex items-center justify-center bg-slate-950 text-slate-600">
                            <i class="fa-solid fa-film text-2xl"></i>
                        </div>
                        `}

                        <!-- Karartma Gradiyenti -->
                        <div class="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-slate-950/60 pointer-events-none"></div>

                        <!-- Sol Üst: Virallik & Tür Rozetleri -->
                        <div class="absolute top-2 left-2 flex items-center gap-1.5 flex-wrap z-10">
                            <span class="text-[11px] font-bold px-2 py-0.5 rounded-lg border ${scoreBadge} flex items-center gap-1 backdrop-blur-md shadow-sm">
                                <i class="fa-solid fa-fire text-xs"></i> ${cand.score}/100
                            </span>
                            ${typeBadge}
                        </div>

                        <!-- Sağ Üst: Hızlı 9:16 Üret Butonu -->
                        <div class="absolute top-2 right-2 z-10">
                            <button type="button" onclick="renderCandidateClip('${cand.id}', this)" id="thumb-render-btn-${cand.id}"
                                class="bg-indigo-600/90 hover:bg-indigo-500 text-white font-semibold text-[11px] px-2.5 py-1 rounded-lg border border-indigo-400/30 flex items-center gap-1.5 shadow-md backdrop-blur-md transition-all active:scale-95 hover:shadow-indigo-500/25">
                                <i class="fa-solid ${isRendered ? 'fa-rotate-right' : 'fa-bolt-lightning text-yellow-300'}"></i>
                                <span>${isRendered ? 'Tekrar' : '9:16 Üret'}</span>
                            </button>
                        </div>

                        <!-- Sağ Alt: Zaman Damgası & Süre -->
                        <div class="absolute bottom-2 right-2 z-10">
                            <span id="cand-clock-${cand.id}" class="text-[11px] text-white/95 font-mono flex items-center gap-1 bg-black/80 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/10 shadow-sm">
                                <i class="fa-regular fa-clock text-slate-300 text-[10px]"></i> [${formatSec(cand.start_time)} - ${formatSec(cand.end_time)}] • ${Math.round(cand.duration)}s
                            </span>
                        </div>

                        <!-- Sol Alt: Durum Rozeti -->
                        <div class="absolute bottom-2 left-2 z-10 flex items-center gap-1">
                            ${renderedStatusBadge}
                        </div>

                        <!-- Render Sırasında Thumbnail Üzerinde Canlı Yükleme Katmanı -->
                        <div id="thumb-render-overlay-${cand.id}" class="hidden absolute inset-0 bg-slate-950/85 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-2 p-3 text-center">
                            <div class="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></div>
                            <span class="text-xs text-indigo-300 font-semibold" id="thumb-overlay-status-${cand.id}">9:16 Kırpılıyor...</span>
                            <span class="text-[10px] text-slate-400 font-mono" id="thumb-overlay-timer-${cand.id}">⏱️ 0s • ⏳ ~${origDur}s</span>
                        </div>
                    </div>

                    <!-- Transkript Önizleme -->
                    ${cand.transcript_snippet ? `
                    <div class="bg-slate-950/80 border border-slate-850 p-3 rounded-xl text-xs sm:text-sm text-slate-300 italic flex items-start gap-2.5">
                        <i class="fa-solid fa-quote-left text-slate-600 text-xs mt-0.5"></i>
                        <span class="line-clamp-2">${escapeHtml(cand.transcript_snippet)}</span>
                    </div>
                    ` : ''}

                    <!-- Metrik Puanları -->
                    <div class="grid grid-cols-3 gap-1.5 text-center py-2 bg-slate-950/60 rounded-xl border border-slate-850 text-xs text-slate-400">
                        <div>Kanca: <strong class="text-white">${cand.hook_score}/10</strong></div>
                        <div>Akış: <strong class="text-white">${cand.flow_score}/10</strong></div>
                        <div>Değer: <strong class="text-white">${cand.value_score}/10</strong></div>
                    </div>

                    <!-- Süre Ölçeği & Uzatma Kontrolleri -->
                    <div class="bg-slate-950/70 border border-slate-850 p-2.5 rounded-xl space-y-2">
                        <div class="flex items-center justify-between text-xs">
                            <span class="text-slate-400 font-medium flex items-center gap-1">
                                <i class="fa-solid fa-clock-rotate-left text-indigo-400"></i> Süre Ölçeği:
                            </span>
                            <span class="font-mono text-indigo-300 font-bold" id="cand-duration-display-${cand.id}">
                                ${formatSec(cand.start_time)} - ${formatSec(cand.end_time)} (${Math.round(cand.duration)}s)
                            </span>
                        </div>

                        <!-- 3 Hızlı Ölçek Butonu -->
                        <div class="grid grid-cols-3 gap-1.5 text-[11px]">
                            <button type="button" onclick="setCandidateScale('${cand.id}', 'short')" id="scale-btn-short-${cand.id}"
                                class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'short' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                <div>⚡ Kısa (${origDur}s)</div>
                                <div class="text-[9px] text-amber-400/90 font-normal">⭐ Önerilen</div>
                            </button>
                            <button type="button" onclick="setCandidateScale('${cand.id}', 'medium')" id="scale-btn-medium-${cand.id}"
                                class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'medium' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                <div>⚖️ Orta (${Math.min(Math.round(videoDur), origDur + 10)}s)</div>
                                <div class="text-[9px] text-indigo-300/80 font-normal">+10s Bağlam</div>
                            </button>
                            <button type="button" onclick="setCandidateScale('${cand.id}', 'long')" id="scale-btn-long-${cand.id}"
                                class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'long' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                <div>📖 Uzun (${Math.min(Math.round(videoDur), origDur + 20)}s)</div>
                                <div class="text-[9px] text-purple-300/80 font-normal">+20s Detaylı</div>
                            </button>
                        </div>

                        <!-- İnce Ayar / Uzatma Butonları -->
                        <div class="flex items-center justify-between pt-1 border-t border-slate-850 text-xs">
                            <span class="text-[10px] text-slate-500">Hassas Ayar:</span>
                            <div class="flex items-center gap-1">
                                <button type="button" onclick="adjustCandidateDuration('${cand.id}', -5)" title="5 saniye kısalt"
                                    class="bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 text-[10px] font-mono transition-colors">
                                    -5s
                                </button>
                                <button type="button" onclick="adjustCandidateDuration('${cand.id}', 5)" title="5 saniye uzat"
                                    class="bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 text-[10px] font-mono transition-colors">
                                    +5s
                                </button>
                                <button type="button" onclick="adjustCandidateDuration('${cand.id}', 10)" title="10 saniye uzat"
                                    class="bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/30 text-[10px] font-semibold transition-colors flex items-center gap-1">
                                    <i class="fa-solid fa-bolt text-yellow-300 text-[9px]"></i> +10s Uzat
                                </button>
                                <button type="button" onclick="resetCandidateDuration('${cand.id}')" title="Orijinal süreye dön"
                                    class="text-slate-500 hover:text-slate-300 p-1 text-[10px] transition-colors ml-1">
                                    <i class="fa-solid fa-rotate-left"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Düzenlenebilir Başlık, Açıklama ve Etiketler Alanı -->
                    <div class="space-y-2.5 pt-1">
                        <div>
                            <div class="flex items-center justify-between mb-1">
                                <label class="text-xs uppercase font-bold text-slate-400">Klip Başlığı</label>
                                <button type="button" onclick="regenerateCandidateMeta('${cand.id}', this)" class="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 py-0.5 px-1">
                                    <i class="fa-solid fa-wand-magic-sparkles"></i> AI ile Yenile
                                </button>
                            </div>
                            <input type="text" id="cand-title-${cand.id}" value="${escapeHtml(cand.title)}"
                                class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-sm text-white font-medium focus:outline-none transition-colors">
                        </div>

                        <div>
                            <label class="text-xs uppercase font-bold text-slate-400 block mb-1">Açıklama</label>
                            <textarea id="cand-desc-${cand.id}" rows="2"
                                class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-2.5 text-sm text-slate-300 focus:outline-none transition-colors resize-none">${escapeHtml(cand.description || '')}</textarea>
                        </div>

                        <div>
                            <label class="text-xs uppercase font-bold text-slate-400 block mb-1">Etiketler (Hashtags)</label>
                            <input type="text" id="cand-tags-${cand.id}" value="${escapeHtml((cand.hashtags || []).join(' '))}"
                                class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-sm text-slate-400 focus:outline-none transition-colors">
                        </div>
                    </div>
                </div>

                <!-- Aksiyon Butonu / İlerleme Kapsayıcısı -->
                <div class="pt-2 border-t border-slate-850" id="render-action-container-${cand.id}">
                    ${isRendered ? `
                    <button type="button" onclick="jumpToRenderedClip('${cand.id}')"
                        class="w-full bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 font-bold py-2.5 px-3 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98] mb-2 shadow-sm">
                        <i class="fa-solid fa-circle-play text-emerald-400"></i>
                        <span>🎬 Üretilen Klibi Gör ${sharedCount > 0 ? `(${sharedCount}/5 Paylaşıldı)` : '& Paylaş'} (${Math.round(cand.duration)}s) ➔</span>
                    </button>
                    ` : ''}
                    <button type="button" id="render-btn-${cand.id}" onclick="renderCandidateClip('${cand.id}', this)"
                        class="w-full ${isRendered ? 'bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs py-2.5' : 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 text-white shadow-lg shadow-indigo-600/20 py-3'} font-semibold px-3 rounded-xl text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98] min-h-[44px]">
                        <i class="fa-solid ${isRendered ? 'fa-rotate-right' : 'fa-bolt-lightning text-yellow-300'}"></i>
                        <span>${isRendered ? 'Tekrar 9:16 Render Et' : '⚡ Bu Klibi Üret (9:16 Render Et)'}</span>
                    </button>
                </div>
            `;

            candidatesGrid.appendChild(card);
        });
    }

    // ==========================================
    // 6. AŞAMA 2: İSTEĞE BAĞLI RENDER ETME
    // ==========================================
    window.renderCandidateClip = async function(candId, btn) {
        if (!currentProject) return;

        const cand = (currentProject.candidates || []).find(c => String(c.id) === String(candId));
        const candDuration = cand ? Math.round(cand.duration || (cand.end_time - cand.start_time) || 30) : 30;
        // Optimize edilmiş 5x hızlı FFmpeg pipeline (yaklaşık %20-25'i kadar)
        const estTotalSec = Math.max(5, Math.round(candDuration * 0.22));

        const titleInput = document.getElementById(`cand-title-${candId}`);
        const descInput = document.getElementById(`cand-desc-${candId}`);
        const tagsInput = document.getElementById(`cand-tags-${candId}`);

        const editedTitle = titleInput ? titleInput.value.trim() : '';
        const editedDesc = descInput ? descInput.value.trim() : '';
        const rawTags = tagsInput ? tagsInput.value.trim() : '';
        const editedTags = rawTags ? rawTags.split(/\s+/).filter(t => t.startsWith('#') || t.length > 0).map(t => t.startsWith('#') ? t : `#${t}`) : [];

        // Aksiyon kapsayıcısını ve tetikleyen butonu belirle
        const isRenderedCardTrigger = Boolean(btn && (btn.id === `rendered-rerender-btn-${candId}` || (btn.closest && btn.closest(`#rendered-card-${candId}`))));
        const actionContainer = isRenderedCardTrigger ? null : (document.getElementById(`render-action-container-${candId}`) || (btn ? btn.parentElement : null));
        const originalActionHtml = actionContainer ? actionContainer.innerHTML : '';
        const origBtnHtml = btn ? btn.innerHTML : '';

        // Thumbnail üzerindeki katman ve buton kontrolleri
        const thumbOverlay = document.getElementById(`thumb-render-overlay-${candId}`);
        const thumbBtn = document.getElementById(`thumb-render-btn-${candId}`);
        const thumbTimer = document.getElementById(`thumb-overlay-timer-${candId}`);
        const thumbStatus = document.getElementById(`thumb-overlay-status-${candId}`);

        if (thumbOverlay) thumbOverlay.classList.remove('hidden');
        if (thumbBtn) {
            thumbBtn.disabled = true;
            thumbBtn.classList.add('opacity-50', 'pointer-events-none');
        }

        if (actionContainer) {
            actionContainer.innerHTML = `
                <div class="bg-slate-950/95 border border-indigo-500/40 rounded-xl p-3.5 space-y-2.5 shadow-xl shadow-indigo-950/40">
                    <div class="flex items-center justify-between text-xs">
                        <span class="font-bold text-indigo-300 flex items-center gap-1.5" id="render-phase-text-${candId}">
                            <i class="fa-solid fa-gear fa-spin text-indigo-400"></i> Klip kesiliyor & FFmpeg hazırlanıyor...
                        </span>
                        <span class="text-slate-300 font-mono text-xs font-semibold bg-slate-900 border border-slate-800 px-2.5 py-0.5 rounded-md" id="render-timer-text-${candId}">
                            ⏱️ 0s • Kalan: ~${estTotalSec}s
                        </span>
                    </div>
                    
                    <!-- İlerleme Çubuğu -->
                    <div class="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800 relative">
                        <div id="render-progress-bar-${candId}" 
                             class="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-700 ease-out rounded-full"
                             style="width: 8%;">
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-between text-xs text-slate-400">
                        <span class="flex items-center gap-1.5" id="render-subtext-${candId}">
                            <span class="w-2 h-2 rounded-full bg-indigo-500 animate-ping inline-block"></span>
                            <span>9:16 Dikey Dönüştürme & Altyazı Giydirme</span>
                        </span>
                        <span class="font-mono text-indigo-300 font-bold" id="render-percent-text-${candId}">%8</span>
                    </div>
                </div>
            `;
        } else if (btn) {
            btn.disabled = true;
            btn.classList.add('opacity-75');
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-sm"></i> <span>${candDuration}s Render Ediliyor... (⏱️ 0s)</span>`;
        }

        showToast('Klip render işlemi başlatıldı, canlı ilerleme takip ediliyor...', 'info');

        let elapsedSec = 0;
        const progressBarEl = document.getElementById(`render-progress-bar-${candId}`);
        const timerTextEl = document.getElementById(`render-timer-text-${candId}`);
        const phaseTextEl = document.getElementById(`render-phase-text-${candId}`);
        const percentTextEl = document.getElementById(`render-percent-text-${candId}`);

        const renderInterval = setInterval(() => {
            elapsedSec += 1;
            const remainingSec = Math.max(1, estTotalSec - elapsedSec);

            // Dinamik yüzdelik hesaplama
            let percent = Math.min(93, Math.round(8 + (elapsedSec / estTotalSec) * 85));
            if (elapsedSec > estTotalSec) {
                percent = Math.min(95, 93 + Math.floor((elapsedSec - estTotalSec) / 4));
            }

            if (progressBarEl) progressBarEl.style.width = `${percent}%`;
            if (percentTextEl) percentTextEl.textContent = `%${percent}`;

            if (timerTextEl) {
                if (elapsedSec < estTotalSec) {
                    timerTextEl.textContent = `⏱️ ${elapsedSec}s • Kalan: ~${remainingSec}s`;
                } else {
                    timerTextEl.textContent = `⏱️ ${elapsedSec}s • Son rötuşlar...`;
                }
            }

            if (isRenderedCardTrigger && btn) {
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-sm"></i> <span>${candDuration}s Render Ediliyor... (⏱️ ${elapsedSec}s)</span>`;
            }

            if (thumbTimer) {
                thumbTimer.textContent = `⏱️ ${elapsedSec}s • ⏳ ~${remainingSec}s`;
            }
            if (thumbStatus && percent >= 50) {
                thumbStatus.textContent = percent < 80 ? 'Altyazı Giydiriliyor...' : 'MP4 Oluşturuluyor...';
            }

            // Aşamalara göre bilgilendirici metinler
            if (phaseTextEl) {
                if (percent < 25) {
                    phaseTextEl.innerHTML = '<i class="fa-solid fa-scissors text-indigo-400"></i> Video hassas zamanla kesiliyor...';
                } else if (percent < 60) {
                    phaseTextEl.innerHTML = '<i class="fa-solid fa-expand text-purple-400"></i> 9:16 dikey format & bulanık arka plan işleniyor...';
                } else if (percent < 85) {
                    phaseTextEl.innerHTML = '<i class="fa-solid fa-closed-captioning text-pink-400"></i> Kelime düzeyinde renkli altyazılar giydiriliyor...';
                } else {
                    phaseTextEl.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles text-amber-400"></i> Ses & video birleştiriliyor, MP4 oluşturuluyor...';
                }
            }
        }, 1000);

        try {
            const res = await fetchWithAuth('/api/render-clip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    candidate_id: candId,
                    vertical_mode: verticalModeInput.value,
                    title: editedTitle,
                    description: editedDesc,
                    hashtags: editedTags,
                    start_time: cand ? cand.start_time : undefined,
                    end_time: cand ? cand.end_time : undefined
                })
            });

            clearInterval(renderInterval);

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Klip render edilemedi.');
            }

            const renderedClip = await res.json();

            // Tamamlandı animasyonu (%100 ve yeşil bildirim)
            if (progressBarEl) {
                progressBarEl.className = 'h-full bg-emerald-500 transition-all duration-300 rounded-full';
                progressBarEl.style.width = '100%';
            }
            if (percentTextEl) percentTextEl.textContent = '%100';
            if (phaseTextEl) {
                phaseTextEl.innerHTML = '<i class="fa-solid fa-circle-check text-emerald-400"></i> 9:16 Klip Başarıyla Oluşturuldu!';
                phaseTextEl.className = 'font-bold text-emerald-400 flex items-center gap-1.5';
            }
            if (timerTextEl) {
                timerTextEl.textContent = `✅ Tamamlandı (${elapsedSec}s)`;
            }
            if (isRenderedCardTrigger && btn) {
                btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span class="text-emerald-300 font-bold">Tamamlandı! (${elapsedSec}s)</span>`;
            }

            const cleanUrl = (renderedClip.video_url || `/api/clips/${renderedClip.video_filename || ('clip_' + candId + '.mp4')}`).split('?')[0];
            renderedClip.rendered_at_ts = renderedClip.rendered_at_ts || Date.now();
            renderedClip.video_url = `${cleanUrl}?v=${renderedClip.rendered_at_ts}`;

            // Candidate durumunu güncelle
            for (let c of currentProject.candidates) {
                if (String(c.id) === String(candId)) {
                    c.is_rendered = true;
                    c.start_time = renderedClip.start_time;
                    c.end_time = renderedClip.end_time;
                    c.duration = renderedClip.duration;
                    c.video_filename = renderedClip.video_filename;
                    c.video_url = renderedClip.video_url;
                    c.rendered_at_ts = renderedClip.rendered_at_ts;
                    c.share_urls = renderedClip.share_urls;
                    break;
                }
            }

            // Rendered listeye ekle veya var olanı güncelle
            let found = false;
            for (let i = 0; i < currentProject.rendered_clips.length; i++) {
                if (String(currentProject.rendered_clips[i].id) === String(candId)) {
                    currentProject.rendered_clips[i] = renderedClip;
                    found = true;
                    break;
                }
            }
            if (!found) {
                currentProject.rendered_clips.unshift(renderedClip);
            }

            showToast('9:16 Video ve altyazı başarıyla üretildi!', 'success');

            // Kullanıcının %100 başarısını görmesi için kısa bir bekleme ve ardından listeleri yenileme
            setTimeout(() => {
                renderFinishedClips(currentProject.rendered_clips);
                renderCandidates(currentProject.candidates);
                loadHistory();

                const freshVid = document.getElementById(`rendered-video-${candId}`);
                if (freshVid) {
                    freshVid.src = renderedClip.video_url;
                    try { freshVid.load(); } catch (e) {}
                }

                // Rozetleri ve sekmeleri güncelle
                if (mainBadgeCandidates) mainBadgeCandidates.textContent = currentProject.candidates.length;
                if (mainBadgeRendered) mainBadgeRendered.textContent = currentProject.rendered_clips.length;
                if (bottomNavRenderedBadge) bottomNavRenderedBadge.classList.remove('hidden');
                if (projectViewTabs) projectViewTabs.classList.remove('hidden');
                if (mobileBottomNav) mobileBottomNav.classList.remove('hidden');

                // Hazır klipler sekmesine geç ve o klibe odaklan
                window.jumpToRenderedClip(candId);
            }, 700);

        } catch (err) {
            clearInterval(renderInterval);
            if (thumbOverlay) thumbOverlay.classList.add('hidden');
            if (thumbBtn) {
                thumbBtn.disabled = false;
                thumbBtn.classList.remove('opacity-50', 'pointer-events-none');
            }
            showToast('Render Hatası: ' + err.message, 'error');
            if (actionContainer && originalActionHtml) {
                actionContainer.innerHTML = originalActionHtml;
            }
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-75');
                btn.innerHTML = origBtnHtml || '<i class="fa-solid fa-rotate-right"></i> <span>Yeniden Render Et</span>';
            }
        }
    };

    // ==========================================
    // 7. AI İLE BAŞLIK & AÇIKLAMA YENİLEME
    // ==========================================
    window.regenerateCandidateMeta = async function(candId, btn) {
        if (!currentProject) return;

        const titleInput = document.getElementById(`cand-title-${candId}`);
        const descInput = document.getElementById(`cand-desc-${candId}`);
        const tagsInput = document.getElementById(`cand-tags-${candId}`);

        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yenileniyor...';

        try {
            const res = await fetchWithAuth('/api/regenerate-meta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    candidate_id: candId,
                    current_title: titleInput ? titleInput.value : ''
                })
            });

            if (!res.ok) throw new Error('Yapay zeka yanıt veremedi.');
            const data = await res.json();

            if (titleInput && data.title) titleInput.value = data.title;
            if (descInput && data.description) descInput.value = data.description;
            if (tagsInput && data.hashtags) tagsInput.value = (data.hashtags || []).join(' ');

            showToast('Yapay zeka yeni başlık ve açıklama üretti!', 'success');
        } catch (err) {
            showToast('Hata: ' + err.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    };

    // ==========================================
    // 8. RENDER EDİLMİŞ KLİPLERİN GÖSTERİMİ
    // ==========================================
    function renderFinishedClips(clips) {
        const count = clips ? clips.length : 0;
        if (renderedCountBadge) renderedCountBadge.textContent = count;
        if (renderedTotalBadge) renderedTotalBadge.textContent = `${count} Klip`;
        if (mainBadgeRendered) mainBadgeRendered.textContent = count;
        if (bottomNavRenderedBadge) {
            if (count > 0) bottomNavRenderedBadge.classList.remove('hidden');
            else bottomNavRenderedBadge.classList.add('hidden');
        }

        if (!clips || clips.length === 0) {
            if (scrollRenderedBtn) scrollRenderedBtn.classList.add('hidden');
            renderedGrid.innerHTML = `
                <div class="col-span-full bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
                    <div class="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
                        <i class="fa-solid fa-clapperboard text-xl"></i>
                    </div>
                    <h4 class="text-sm sm:text-base font-bold text-white">Henüz Üretilmiş Klip Bulunmuyor</h4>
                    <p class="text-xs text-slate-400 max-w-md mx-auto">Aday kesitler sekmesinden beğendiğiniz bir bölümün '9:16 Üret' butonuna basarak klibinizi oluşturabilirsiniz.</p>
                    <div class="pt-2">
                        <button type="button" onclick="window.switchMainView('candidates')" 
                            class="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-xl text-xs flex items-center gap-2 mx-auto transition-all shadow-md active:scale-95 cursor-pointer">
                            <i class="fa-solid fa-list-check"></i> <span>Aday Kesitlere Git</span>
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        if (renderedContainer) renderedContainer.classList.remove('hidden');
        if (scrollRenderedBtn) scrollRenderedBtn.classList.remove('hidden');
        renderedGrid.innerHTML = '';

        const SOCIAL_PLATFORMS = [
            { id: 'instagram', name: 'Instagram', shortName: 'Instagram', icon: 'fa-brands fa-instagram', color: 'text-pink-400', activeBadge: 'bg-pink-500/20 text-pink-300 border-pink-500/30' },
            { id: 'tiktok', name: 'TikTok', shortName: 'TikTok', icon: 'fa-brands fa-tiktok', color: 'text-cyan-400', activeBadge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
            { id: 'youtube', name: 'Shorts', shortName: 'Shorts', icon: 'fa-brands fa-youtube', color: 'text-red-500', activeBadge: 'bg-red-500/20 text-red-300 border-red-500/30' },
            { id: 'twitter', name: 'X (Twitter)', shortName: 'X', icon: 'fa-brands fa-x-twitter', color: 'text-white', activeBadge: 'bg-slate-800 text-slate-100 border-slate-600' },
            { id: 'bluesky', name: 'Bluesky', shortName: 'Bluesky', icon: 'fa-brands fa-bluesky', color: 'text-sky-400', activeBadge: 'bg-sky-500/20 text-sky-300 border-sky-500/30' }
        ];

        clips.forEach((clip, idx) => {
            const card = document.createElement('div');
            card.className = 'bg-slate-900 border border-slate-800/90 rounded-2xl overflow-hidden shadow-2xl flex flex-col transition-all';
            card.id = `rendered-card-${clip.id}`;

            const cand = (currentProject.candidates || []).find(c => String(c.id) === String(clip.id));
            const origDur = cand && cand.orig_duration ? Math.round(cand.orig_duration) : Math.round(clip.duration || 30);
            const activeScale = cand ? (cand.active_scale || 'short') : 'short';
            const videoDur = (currentProject.duration && currentProject.duration > 0) ? currentProject.duration : 99999;
            const isDownloaded = window.isClipDownloaded(clip.id);

            const sharedList = (clip.shared_platforms || []).map(p => p === 'x' ? 'twitter' : p);
            const sharedCount = SOCIAL_PLATFORMS.filter(p => sharedList.includes(p.id)).length;
            const missingCount = SOCIAL_PLATFORMS.length - sharedCount;
            const isAllShared = sharedCount === SOCIAL_PLATFORMS.length;

            const cleanUrl = (clip.video_url || `/api/clips/${clip.video_filename || ('clip_' + clip.id + '.mp4')}`).split('?')[0];
            const videoSrcWithCacheBust = `${cleanUrl}?v=${clip.rendered_at_ts || Date.now()}`;

            card.innerHTML = `
                <!-- 9:16 Video Player -->
                <div class="video-player-container relative">
                    <video id="rendered-video-${clip.id}" controls playsinline preload="metadata" loop onplay="pauseOtherVideos(this)" src="${videoSrcWithCacheBust}" class="w-full h-full object-cover">
                        Tarayıcınız video oynatmayı desteklemiyor.
                    </video>
                    <!-- Safe-Zone Rehberi (Reels / TikTok Arayüz Alanı) -->
                    <div class="safe-zone-overlay hidden absolute inset-0 pointer-events-none flex flex-col justify-between p-3 border-2 border-dashed border-amber-400/60 z-10">
                        <div class="text-[9px] font-bold text-amber-300 bg-black/70 px-2 py-0.5 rounded self-start backdrop-blur-sm">
                            📱 ÜST GÜVENLİ ALAN (Kullanıcı / Hikaye Çizgisi)
                        </div>
                        <div class="flex justify-between items-end">
                            <div class="text-[9px] font-bold text-amber-300 bg-black/70 px-2 py-0.5 rounded backdrop-blur-sm max-w-[65%]">
                                💬 ALT AÇIKLAMA ALANI (Altyazılar bu alanın üstünde)
                            </div>
                            <div class="text-[9px] font-bold text-amber-300 bg-black/70 px-1.5 py-0.5 rounded backdrop-blur-sm text-right">
                                ❤️ BUTONLAR
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Kart İçeriği -->
                <div class="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-4">
                    
                    <!-- Başlık & Skor & Kaynak Aday Köprüsü -->
                    <div class="space-y-3">
                        <!-- Kaynak Aday Bilgisi & Köprü Butonu -->
                        <div class="flex items-center justify-between text-xs text-slate-400 bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-850">
                            <span class="flex items-center gap-1.5 font-medium">
                                <i class="fa-solid fa-layer-group text-indigo-400"></i>
                                <span>Klip <strong>#${idx + 1}</strong> (${clip.duration}s)</span>
                            </span>
                            <button type="button" onclick="jumpToCandidateClip('${clip.id}')"
                                class="text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 hover:underline">
                                <span>Aday Kesite Git</span>
                                <i class="fa-solid fa-arrow-right text-[10px]"></i>
                            </button>
                        </div>

                        <div class="flex items-center justify-between flex-wrap gap-2">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs font-bold px-2.5 py-1 rounded-full border border-emerald-500/40 bg-emerald-500/15 text-emerald-300 flex items-center gap-1">
                                    <i class="fa-solid fa-fire text-xs"></i> Virallik: ${clip.score}/100
                                </span>
                                ${clip.is_shared ? `
                                <div class="flex items-center gap-1">
                                    <span class="text-xs font-bold px-2.5 py-1 rounded-full border border-emerald-500/40 bg-emerald-500/25 text-emerald-300 flex items-center gap-1.5 shadow-sm">
                                        <i class="fa-solid fa-circle-check text-emerald-400"></i>
                                        <span>${sharedCount}/5 Paylaşıldı</span>
                                        ${sharedCount < 5 ? `<span class="text-[10px] text-amber-300 font-normal">(${missingCount} Eksik)</span>` : '<span class="text-[10px] text-emerald-200 font-normal">🎉 Tam</span>'}
                                    </span>
                                    <button type="button" onclick="toggleClipShared('${clip.id}')" title="Tüm paylaşım işaretlerini kaldır" class="text-[11px] text-slate-500 hover:text-rose-400 p-1 transition-colors">
                                        <i class="fa-solid fa-xmark"></i>
                                    </button>
                                </div>
                                ` : `
                                <button type="button" onclick="toggleClipShared('${clip.id}')" title="Tümünü paylaşıldı olarak işaretle" class="text-xs text-amber-300/90 hover:text-white border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 px-2.5 py-1 rounded-full flex items-center gap-1.5 transition-all">
                                    <i class="fa-regular fa-circle-check text-amber-400"></i> <span>5 Platform Eksik</span>
                                </button>
                                `}
                                <button type="button" onclick="toggleSafeZone('${clip.id}', this)" class="text-xs text-slate-400 hover:text-slate-200 border border-slate-700 bg-slate-800 px-2.5 py-1 rounded-full flex items-center gap-1 transition-all">
                                    <i class="fa-solid fa-mobile-screen-button"></i> Safe-Zone
                                </button>
                            </div>
                            <span class="text-xs text-slate-400 font-mono bg-slate-950/80 px-2.5 py-1 rounded-md border border-slate-850">
                                <i class="fa-regular fa-clock"></i> ${clip.duration}s
                            </span>
                        </div>

                        <!-- Doğrudan Klipten Süre Değiştirme & Yeniden Render Etme -->
                        <div class="bg-slate-950/70 border border-slate-850 p-2.5 rounded-xl space-y-2">
                            <div class="flex items-center justify-between text-xs">
                                <span class="text-slate-300 font-semibold flex items-center gap-1.5">
                                    <i class="fa-solid fa-clock-rotate-left text-indigo-400"></i> Süreyi Değiştir & Yeniden Üret:
                                </span>
                                <span class="font-mono text-indigo-300 font-bold" id="rendered-duration-display-${clip.id}">
                                    ${cand ? `${formatSec(cand.start_time)} - ${formatSec(cand.end_time)} (${Math.round(cand.duration)}s)` : `${Math.round(clip.duration)}s`}
                                </span>
                            </div>

                            <!-- 3 Hızlı Ölçek Butonu -->
                            <div class="grid grid-cols-3 gap-1.5 text-[11px]">
                                <button type="button" onclick="setRenderedClipScale('${clip.id}', 'short')" id="rendered-scale-short-${clip.id}"
                                    class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'short' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                    <div>⚡ Kısa (${origDur}s)</div>
                                    <div class="text-[9px] text-amber-400/90 font-normal">⭐ Önerilen</div>
                                </button>
                                <button type="button" onclick="setRenderedClipScale('${clip.id}', 'medium')" id="rendered-scale-medium-${clip.id}"
                                    class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'medium' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                    <div>⚖️ Orta (${Math.min(Math.round(videoDur), origDur + 10)}s)</div>
                                    <div class="text-[9px] text-indigo-300/80 font-normal">+10s Bağlam</div>
                                </button>
                                <button type="button" onclick="setRenderedClipScale('${clip.id}', 'long')" id="rendered-scale-long-${clip.id}"
                                    class="scale-btn py-1.5 px-1 rounded-lg border text-center font-medium transition-all ${activeScale === 'long' ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold' : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'}">
                                    <div>📖 Uzun (${Math.min(Math.round(videoDur), origDur + 20)}s)</div>
                                    <div class="text-[9px] text-purple-300/80 font-normal">+20s Detaylı</div>
                                </button>
                            </div>

                            <!-- İnce Ayar Butonları ve Yeniden Render Butonu -->
                            <div class="flex items-center justify-between pt-1 border-t border-slate-850 text-xs gap-2">
                                <div class="flex items-center gap-1">
                                    <button type="button" onclick="adjustRenderedClipDuration('${clip.id}', -5)" title="5 saniye kısalt"
                                        class="bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 text-[10px] font-mono transition-colors">
                                        -5s
                                    </button>
                                    <button type="button" onclick="adjustRenderedClipDuration('${clip.id}', 5)" title="5 saniye uzat"
                                        class="bg-slate-900 hover:bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-800 text-[10px] font-mono transition-colors">
                                        +5s
                                    </button>
                                    <button type="button" onclick="adjustRenderedClipDuration('${clip.id}', 10)" title="10 saniye uzat"
                                        class="bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/30 text-[10px] font-semibold transition-colors flex items-center gap-1">
                                        <i class="fa-solid fa-bolt text-yellow-300 text-[9px]"></i> +10s
                                    </button>
                                </div>
                                <button type="button" id="rendered-rerender-btn-${clip.id}" onclick="reRenderFinishedClip('${clip.id}', this)"
                                    class="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs px-3 py-1.5 rounded-lg border border-indigo-400/30 flex items-center gap-1.5 shadow-md active:scale-95 transition-all">
                                    <i class="fa-solid fa-rotate-right"></i>
                                    <span>${cand ? Math.round(cand.duration) : Math.round(clip.duration)}s Yeniden Render</span>
                                </button>
                            </div>
                        </div>

                        <!-- Düzenlenebilir Alanlar (Son Değişiklik Paylaşıma Yansır) -->
                        <div class="space-y-2.5 pt-1">
                            <div>
                                <label class="text-xs uppercase font-bold text-slate-400 block mb-1">Klip Başlığı</label>
                                <input type="text" id="final-title-${clip.id}" value="${escapeHtml(clip.title)}"
                                    onchange="saveClipTextChanges('${clip.id}')"
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-medium focus:border-indigo-500 focus:outline-none transition-colors">
                            </div>

                            <div>
                                <label class="text-xs uppercase font-bold text-slate-400 block mb-1">Açıklama (YouTube linki otomatik eklenir)</label>
                                <textarea id="final-desc-${clip.id}" rows="2"
                                    onchange="saveClipTextChanges('${clip.id}')"
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-sm text-slate-300 focus:border-indigo-500 focus:outline-none resize-none transition-colors">${escapeHtml(clip.description || '')}</textarea>
                            </div>

                            <div>
                                <label class="text-xs uppercase font-bold text-slate-400 block mb-1">Etiketler</label>
                                <input type="text" id="final-tags-${clip.id}" value="${escapeHtml((clip.hashtags || []).join(' '))}"
                                    onchange="saveClipTextChanges('${clip.id}')"
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-400 focus:border-indigo-500 focus:outline-none transition-colors">
                            </div>
                        </div>

                    </div>

                    <!-- BÜTÜNLEŞİK SOSYAL MEDYA PAYLAŞIM ALANI -->
                    <div class="space-y-2.5 pt-2 border-t border-slate-850">
                        
                        <!-- 🚀 1. Ana Aksiyon: Telefonda Doğrudan Paylaşım (Web Share API ile Video Doğrudan Gönderilir) -->
                        <button onclick="shareClipDirectly('${clip.id}', this)" 
                            class="w-full bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white text-sm font-bold py-3 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-purple-600/25 active:scale-[0.98] transition-all min-h-[46px]">
                            <i class="fa-solid fa-paper-plane text-sm"></i>
                            <span>Telefonda Doğrudan Paylaş (Reels / TikTok / Shorts)</span>
                        </button>

                        <!-- 2. Hızlı Aksiyonlar: Metni Kopyala & MP4 İndir -->
                        <div class="grid grid-cols-2 gap-2">
                            <button onclick="copyEditedCaption('${clip.id}', this)"
                                class="bg-slate-800 hover:bg-slate-750 border border-slate-750 text-indigo-300 hover:text-white text-xs font-semibold py-2.5 px-2 rounded-xl flex items-center justify-center gap-1.5 transition-colors min-h-[40px] active:scale-95">
                                <i class="fa-regular fa-copy text-xs"></i>
                                <span>Metni Kopyala</span>
                            </button>
                            <a href="${videoSrcWithCacheBust}" download="${clip.video_filename}" id="mp4-dl-btn-${clip.id}" onclick="markClipDownloaded('${clip.id}')"
                                class="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-white text-xs font-semibold py-2.5 px-2 rounded-xl flex items-center justify-center gap-1.5 transition-colors min-h-[40px] active:scale-95">
                                <i class="fa-solid ${isDownloaded ? 'fa-circle-check text-emerald-400' : 'fa-download text-indigo-400'} text-xs"></i>
                                <span>${isDownloaded ? 'Tekrar İndir' : 'MP4 İndir'}</span>
                            </a>
                        </div>

                        <!-- 3. Bütünleşik Platform Matrisi: Hem Paylaşım Butonu Hem Canlı Durum Tik'i (Tek Blok) -->
                        <div class="bg-slate-950/80 border border-slate-850 p-2.5 rounded-xl space-y-2">
                            <div class="flex items-center justify-between text-xs px-0.5">
                                <span class="text-slate-400 font-medium flex items-center gap-1.5">
                                    <i class="fa-solid fa-share-nodes text-indigo-400"></i> Platform Paylaşım Durumu:
                                </span>
                                <span class="text-[11px] font-mono font-bold px-2 py-0.5 rounded-full ${isAllShared ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : (sharedCount > 0 ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'bg-slate-800 text-slate-400')}">
                                    ${sharedCount}/5 Paylaşıldı ${missingCount > 0 ? `<span class="text-amber-300 font-normal">(${missingCount} Eksik)</span>` : '🎉'}
                                </span>
                            </div>

                            <div class="grid grid-cols-5 gap-1.5 text-center">
                                ${SOCIAL_PLATFORMS.map(sp => {
                                    const isSharedThis = sharedList.includes(sp.id);
                                    return `
                                    <div onclick="handlePlatformAction('${sp.id}', '${clip.id}', this)"
                                        title="${sp.name}: ${isSharedThis ? 'Paylaşıldı (Kaldırmak için dokun)' : 'Paylaş veya işaretle'}"
                                        class="cursor-pointer py-2 px-1 rounded-xl border transition-all active:scale-95 flex flex-col items-center justify-between gap-1 min-h-[58px] select-none ${isSharedThis ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200 shadow-sm' : 'border-slate-800 bg-slate-900/90 text-slate-400 hover:border-slate-700'}">
                                        <i class="${sp.icon} text-sm ${isSharedThis ? 'text-emerald-400' : sp.color}"></i>
                                        <span class="text-[10px] font-medium leading-none truncate max-w-full">${sp.shortName}</span>
                                        <span class="text-[9px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 ${isSharedThis ? 'bg-emerald-500/30 text-emerald-200' : 'bg-amber-500/15 text-amber-300 border border-amber-500/25'}">
                                            ${isSharedThis ? '<i class=\"fa-solid fa-check text-[7px]\"></i> Var' : 'Eksik'}
                                        </span>
                                    </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>

                        <!-- Klibi Sil Butonu -->
                        <button onclick="deleteSingleClip('${clip.id}')" 
                            class="w-full text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 py-1.5 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors min-h-[34px]">
                            <i class="fa-solid fa-trash text-xs"></i> Bu Klibi Sil
                        </button>

                    </div>
                </div>
            `;

            renderedGrid.appendChild(card);
            preloadClipFile(clip.id, videoSrcWithCacheBust, clip.video_filename);
        });
    }

    // ==========================================
    // 8.5. PAYLAŞILDI DURUMU YÖNETİMİ
    // ==========================================
    window.markClipAsShared = async function(clipId, platform = 'native', isShared = true) {
        if (!currentProject) return;
        const normPlatform = platform === 'x' ? 'twitter' : platform;

        const clip = (currentProject.rendered_clips || []).find(c => String(c.id) === String(clipId));
        if (clip) {
            if (!clip.shared_platforms) clip.shared_platforms = [];
            if (isShared) {
                clip.is_shared = true;
                clip.shared_at = new Date().toISOString();
                if (normPlatform && !clip.shared_platforms.includes(normPlatform)) {
                    clip.shared_platforms.push(normPlatform);
                }
            } else {
                if (normPlatform === 'all' || normPlatform === 'manual' || normPlatform === 'native') {
                    clip.shared_platforms = [];
                } else {
                    clip.shared_platforms = clip.shared_platforms.filter(p => p !== normPlatform);
                }
                clip.is_shared = clip.shared_platforms.length > 0;
            }
        }
        const cand = (currentProject.candidates || []).find(c => String(c.id) === String(clipId));
        if (cand) {
            if (!cand.shared_platforms) cand.shared_platforms = [];
            if (isShared) {
                cand.is_shared = true;
                cand.shared_at = new Date().toISOString();
                if (normPlatform && !cand.shared_platforms.includes(normPlatform)) {
                    cand.shared_platforms.push(normPlatform);
                }
            } else {
                if (normPlatform === 'all' || normPlatform === 'manual' || normPlatform === 'native') {
                    cand.shared_platforms = [];
                } else {
                    cand.shared_platforms = cand.shared_platforms.filter(p => p !== normPlatform);
                }
                cand.is_shared = cand.shared_platforms.length > 0;
            }
        }

        renderFinishedClips(currentProject.rendered_clips);
        renderCandidates(currentProject.candidates);

        try {
            await fetchWithAuth('/api/clips/mark-shared', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    clip_id: clipId,
                    platform: normPlatform,
                    is_shared: isShared
                })
            });
        } catch (e) {
            console.error('Failed to persist shared status:', e);
        }
    };

    window.togglePlatformShared = function(clipId, platform) {
        if (!currentProject) return;
        const normPlatform = platform === 'x' ? 'twitter' : platform;
        const clip = (currentProject.rendered_clips || []).find(c => String(c.id) === String(clipId));
        const sList = (clip && clip.shared_platforms) || [];
        const isCurrentlyShared = sList.includes(normPlatform);
        const newStatus = !isCurrentlyShared;

        window.markClipAsShared(clipId, normPlatform, newStatus);
        const pName = formatPlatformName(normPlatform);
        showToast(newStatus ? `✓ ${pName} paylaşıldı olarak işaretlendi!` : `${pName} paylaşım işareti kaldırıldı.`, 'info');
    };

    window.toggleClipShared = function(clipId) {
        if (!currentProject) return;
        const clip = (currentProject.rendered_clips || []).find(c => String(c.id) === String(clipId));
        const newStatus = clip ? !clip.is_shared : true;
        if (!newStatus) {
            markClipAsShared(clipId, 'all', false);
            showToast('Tüm platform paylaşım işaretleri kaldırıldı.', 'info');
        } else {
            markClipAsShared(clipId, 'manual', true);
            showToast('Klip genel paylaşıldı olarak işaretlendi!', 'info');
        }
    };

    // ==========================================
    // 9. DİNAMİK METİN GÜNCELLEME VE PAYLAŞIM
    // ==========================================
    function getLatestClipCaption(clipId) {
        const titleElem = document.getElementById(`final-title-${clipId}`);
        const descElem = document.getElementById(`final-desc-${clipId}`);
        const tagsElem = document.getElementById(`final-tags-${clipId}`);

        const title = titleElem ? titleElem.value.trim() : '';
        let desc = descElem ? descElem.value.trim() : '';
        const tags = tagsElem ? tagsElem.value.trim() : '';

        // YouTube URL garantisi (açıklamada yoksa ekle)
        const ytUrl = (currentProject && currentProject.youtube_url) ? currentProject.youtube_url : '';
        if (ytUrl && !desc.includes(ytUrl)) {
            desc = desc ? `${desc}\n\n🎬 Videonun tamamı: ${ytUrl}` : `🎬 Videonun tamamı: ${ytUrl}`;
            if (descElem) descElem.value = desc;
        }

        const parts = [title, desc, tags].filter(Boolean);
        return {
            title: title,
            description: desc,
            hashtags: tags ? tags.split(/\s+/) : [],
            fullCaption: parts.join('\n\n').trim()
        };
    }

    window.saveClipTextChanges = async function(clipId) {
        if (!currentProject) return;
        const captionInfo = getLatestClipCaption(clipId);
        try {
            await fetchWithAuth('/api/clips/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    clip_id: clipId,
                    title: captionInfo.title,
                    description: captionInfo.description,
                    hashtags: captionInfo.hashtags
                })
            });
        } catch (e) {
            console.error('Save text error:', e);
        }
    };

    window.copyEditedCaption = function(clipId, btn) {
        const captionInfo = getLatestClipCaption(clipId);
        navigator.clipboard.writeText(captionInfo.fullCaption).then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i> Metin Kopyalandı!';
            showToast('Başlık, açıklama ve etiketler panoya kopyalandı!', 'success');
            setTimeout(() => { btn.innerHTML = orig; }, 2000);
        });
    };

    window.goToHomePage = function() {
        if (historyDrawer && !historyDrawer.classList.contains('hidden')) {
            historyDrawer.classList.add('hidden');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        const urlInput = document.getElementById('video-url');
        if (urlInput) {
            setTimeout(() => urlInput.focus(), 250);
        }
    };

    window.clipFilesCache = window.clipFilesCache || {};
    window.trailerFilesCache = window.trailerFilesCache || {};

    window.preloadClipFile = function(clipId, url, filename) {
        if (!clipId || !url || window.clipFilesCache[clipId]) return;
        fetch(url)
            .then(res => res.ok ? res.blob() : null)
            .then(blob => {
                if (blob) {
                    const fname = filename || `clip_${clipId}.mp4`;
                    window.clipFilesCache[clipId] = new File([blob], fname, { type: 'video/mp4' });
                }
            })
            .catch(() => {});
    };

    window.preloadTrailerFile = function(trailerId, url, filename) {
        if (!trailerId || !url || window.trailerFilesCache[trailerId]) return;
        fetch(url)
            .then(res => res.ok ? res.blob() : null)
            .then(blob => {
                if (blob) {
                    const fname = filename || `trailer_${trailerId}.mp4`;
                    window.trailerFilesCache[trailerId] = new File([blob], fname, { type: 'video/mp4' });
                }
            })
            .catch(() => {});
    };

    window.shareClipDirectly = async function(clipId, btn) {
        if (!currentProject) return;
        const clip = currentProject.rendered_clips.find(c => c.id === clipId);
        if (!clip) return;

        const captionInfo = getLatestClipCaption(clipId);
        saveClipTextChanges(clipId);

        // 1. Her zaman açıklamayı panoya kopyala
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(captionInfo.fullCaption);
            }
        } catch (e) {}

        const cleanUrl = (clip.video_url || `/api/clips/${clip.video_filename || ('clip_' + clip.id + '.mp4')}`).split('?')[0];
        const fetchUrl = `${cleanUrl}?v=${clip.rendered_at_ts || Date.now()}`;
        const filename = clip.video_filename || `clip_${clip.id}.mp4`;

        // 2. Video zaten önceden indirilip hafızaya alınmış mı? (0ms Instant Share - User Gesture %100 Taze!)
        let cachedFile = window.clipFilesCache && window.clipFilesCache[clipId];
        if (cachedFile) {
            if (navigator.canShare && navigator.canShare({ files: [cachedFile] })) {
                try {
                    await navigator.share({
                        files: [cachedFile],
                        title: captionInfo.title,
                        text: captionInfo.fullCaption
                    });
                    markClipAsShared(clipId, 'native', true);
                    markClipDownloaded(clipId);
                    showToast('🎉 Paylaşım menüsü açıldı! Açıklama panoya kopyalandı.', 'success');
                    if (btn) {
                        btn.className = 'w-full bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white text-sm font-bold py-3 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-purple-600/25 active:scale-[0.98] transition-all min-h-[46px]';
                        btn.innerHTML = '<i class="fa-solid fa-paper-plane text-sm"></i> <span>Telefonda Doğrudan Paylaş (Reels / TikTok / Shorts)</span>';
                    }
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        console.warn('Share error with cached file, falling back to link/text share:', err);
                        if (navigator.share) {
                            try {
                                await navigator.share({
                                    title: captionInfo.title,
                                    text: captionInfo.fullCaption,
                                    url: window.location.origin + cleanUrl
                                });
                                markClipAsShared(clipId, 'native', true);
                                showToast('📋 Açıklama panoya kopyalandı! Paylaşım menüsü açıldı.', 'success');
                                return;
                            } catch (e2) {}
                        }
                        showToast('📋 Açıklama panoya kopyalandı! Klibi galerinizden seçebilirsiniz.', 'info');
                    }
                }
                return;
            } else if (navigator.share) {
                try {
                    await navigator.share({
                        title: captionInfo.title,
                        text: captionInfo.fullCaption,
                        url: window.location.origin + cleanUrl
                    });
                    markClipAsShared(clipId, 'native', true);
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        console.warn('Link share error:', err);
                    }
                }
                return;
            }
        }

        // 3. Hafızada henüz yoksa: Arka planda indir ve butonu 'Şimdi Aç' moduna geçir
        // (Doğrudan çağrılırsa ağ gecikmesinden ötürü Android 'Must be handling a user gesture' hatası verir!)
        const originalHtml = btn ? btn.innerHTML : '';
        const originalClass = btn ? btn.className : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i> <span>Video Hazırlanıyor...</span>';
        }

        try {
            showToast('📋 Açıklama kopyalandı! Video hazırlanıyor...', 'info');
            const response = await fetch(fetchUrl);
            if (!response.ok) throw new Error('Video dosyası indirilemedi.');
            const blob = await response.blob();
            const file = new File([blob], filename, { type: 'video/mp4' });
            window.clipFilesCache[clipId] = file;

            // Gesture süresinin dolmasına karşı: Butonu yeşil yap ve 'Şimdi Dokunun' de
            if (btn) {
                btn.disabled = false;
                btn.className = 'w-full bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 text-white text-sm font-bold py-3 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/30 active:scale-[0.98] transition-all min-h-[46px] animate-pulse';
                btn.innerHTML = '<i class="fa-solid fa-paper-plane text-sm"></i> <span>✅ Hazır! Menüyü Açmak İçin Dokunun</span>';
            }
            showToast('✅ Video hazır! Paylaşım menüsünü açmak için butona dokunun.', 'success');
        } catch (err) {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
                btn.className = originalClass;
            }
            showToast('Video hazırlanamadı: ' + err.message, 'error');
            downloadFallback(cleanUrl, filename);
        }
    };

    window.handlePlatformAction = async function(platform, clipId, btn) {
        if (!currentProject) return;
        const clip = currentProject.rendered_clips.find(c => c.id === clipId);
        if (!clip) return;

        const normPlatform = platform === 'x' ? 'twitter' : platform;
        const sharedList = (clip.shared_platforms || []).map(p => p === 'x' ? 'twitter' : p);
        const isSharedThis = sharedList.includes(normPlatform);

        // Zaten işaretlenmişse tek dokunuşla işareti kaldır (toggle)
        if (isSharedThis) {
            markClipAsShared(clipId, normPlatform, false);
            showToast(`${normPlatform.toUpperCase()} işareti kaldırıldı.`, 'info');
            return;
        }

        // Paylaşım başlat
        const captionInfo = getLatestClipCaption(clipId);
        saveClipTextChanges(clipId);

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(captionInfo.fullCaption);
            }
        } catch (e) {}

        // Video odaklı platformlar: Instagram, TikTok, YouTube Shorts
        if (['instagram', 'tiktok', 'youtube'].includes(normPlatform)) {
            const pName = normPlatform === 'instagram' ? 'Instagram' : (normPlatform === 'tiktok' ? 'TikTok' : 'Shorts');
            showToast(`📋 Açıklama panoya kopyalandı! Açılan menüden ${pName}'i seçin.`, 'info');
            markClipAsShared(clipId, normPlatform, true);
            await window.shareClipDirectly(clipId, btn);
            return;
        }

        // Metin odaklı platformlar: Twitter / X
        if (normPlatform === 'twitter') {
            const ytUrl = (currentProject && currentProject.youtube_url) ? currentProject.youtube_url : '';
            const linkPart = ytUrl ? `\n\n🎬 ${ytUrl}` : '';
            const tags = (captionInfo.hashtags || []).slice(0, 4).join(' ');
            const tweetText = `${captionInfo.title}${linkPart}\n\n${tags}`.trim();
            const tweetUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`;
            markClipAsShared(clipId, 'twitter', true);
            showToast('📋 Açıklama kopyalandı! X (Twitter) açılıyor...', 'success');
            window.open(tweetUrl, '_blank');
            return;
        }

        // Metin odaklı platformlar: Bluesky
        if (normPlatform === 'bluesky') {
            const ytUrl = (currentProject && currentProject.youtube_url) ? currentProject.youtube_url : '';
            const linkPart = ytUrl ? `\n\n🎬 ${ytUrl}` : '';
            const tags = (captionInfo.hashtags || []).slice(0, 4).join(' ');
            const bskyText = `${captionInfo.title}${linkPart}\n\n${tags}`.trim();
            const bskyUrl = `https://bsky.app/intent/compose?text=${encodeURIComponent(bskyText)}`;
            markClipAsShared(clipId, 'bluesky', true);
            showToast('📋 Açıklama kopyalandı! Bluesky açılıyor...', 'success');
            window.open(bskyUrl, '_blank');
            return;
        }
    };

    window.openPlatformDirect = function(platform, clipId, btn) {
        return window.handlePlatformAction(platform, clipId, btn);
    };

    // ==========================================
    // 10. DAHA FAZLA ADAY İSTEĞİ (+10 KLİP)
    // ==========================================
    loadMoreCandidatesBtn.addEventListener('click', async () => {
        if (!currentProject) return;

        const origHtml = loadMoreCandidatesBtn.innerHTML;
        loadMoreCandidatesBtn.disabled = true;
        loadMoreCandidatesBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Yapay zeka transkripti inceliyor...</span>';

        try {
            const res = await fetchWithAuth('/api/candidates/more', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    count: 10
                })
            });

            if (!res.ok) throw new Error('Yeni adaylar yüklenemedi.');
            const data = await res.json();

            const prevLen = (currentProject.candidates || []).length;
            currentProject.candidates = data.candidates;
            const added = data.added_count !== undefined ? data.added_count : (currentProject.candidates.length - prevLen);

            if (activeCandidateTab === 'search' || activeCandidateTab === 'custom') {
                activeCandidateTab = 'ai';
            }
            renderCandidates(currentProject.candidates);

            if (added > 0) {
                showToast(`Yeni ${added} adet benzersiz viral aday eklendi!`, 'success');
                if (data.new_first_id) {
                    setTimeout(() => {
                        const targetCard = document.getElementById(`candidate-card-${data.new_first_id}`) || 
                                           document.querySelector(`[data-candidate-id="${data.new_first_id}"]`);
                        if (targetCard) {
                            targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }, 150);
                }
            } else {
                showToast('Tüm video zaten tarandı, çakışmayan yeni kesit kalmadı.', 'info');
            }
        } catch (err) {
            showToast('Hata: ' + err.message, 'error');
        } finally {
            loadMoreCandidatesBtn.disabled = false;
            loadMoreCandidatesBtn.innerHTML = origHtml;
        }
    });

    // Aday Sekme Filtreleme Tıklama Olayı
    const candidateFilterTabs = document.getElementById('candidate-filter-tabs');
    if (candidateFilterTabs) {
        candidateFilterTabs.addEventListener('click', (e) => {
            const btn = e.target.closest('.candidate-filter-btn');
            if (!btn) return;
            const targetFilter = btn.getAttribute('data-filter') || 'all';
            activeCandidateTab = targetFilter;
            if (currentProject && currentProject.candidates) {
                renderCandidates(currentProject.candidates);
            }
        });
    }

    // ==========================================
    // 10.1 VİDEODA KONU / KELİME ARAMA & KIRPMA
    // ==========================================
    const topicSearchInput = document.getElementById('topic-search-input');
    const topicSearchBtn = document.getElementById('topic-search-btn');
    const topicSearchRenderBtn = document.getElementById('topic-search-render-btn');
    const toggleManualCutBtn = document.getElementById('toggle-manual-cut-btn');
    const manualCutFields = document.getElementById('manual-cut-fields');
    const manualCutArrow = document.getElementById('manual-cut-arrow');
    const manualStartInput = document.getElementById('manual-start-input');
    const manualEndInput = document.getElementById('manual-end-input');
    const manualCutBtn = document.getElementById('manual-cut-btn');

    async function executeTopicSearch(autoRenderFirst = false) {
        if (!currentProject) {
            showToast('Lütfen önce bir video analiz edin veya geçmişten açın.', 'info');
            return;
        }

        const query = topicSearchInput ? topicSearchInput.value.trim() : '';
        if (!query) {
            showToast('Lütfen aramak istediğiniz bir konu veya kelime yazın.', 'info');
            return;
        }

        const activeBtn = autoRenderFirst ? topicSearchRenderBtn : topicSearchBtn;
        const origHtml = activeBtn ? activeBtn.innerHTML : '';
        if (activeBtn) {
            activeBtn.disabled = true;
            activeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>' + (autoRenderFirst ? 'Aranıyor & Kırpılıyor...' : 'Konu Aranıyor...') + '</span>';
        }

        try {
            const res = await fetchWithAuth('/api/search-topic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    query: query
                })
            });

            if (!res.ok) throw new Error('Arama sırasında hata oluştu.');
            const data = await res.json();

            if (!data.matched_candidates || data.matched_candidates.length === 0) {
                showToast(data.message || 'Bu konuyla ilgili net bir kesit bulunamadı.', 'info');
                return;
            }

            currentProject.candidates = data.candidates || currentProject.candidates;
            activeCandidateTab = 'search';
            renderCandidates(currentProject.candidates);

            showToast(`"${query}" konusuyla ilgili ${data.matched_candidates.length} kesit bulundu!`, 'success');

            // Eğer "Bul ve Hemen Kırp" tıklandıysa, bulunan ilk kesiti otomatik render et
            if (autoRenderFirst && data.matched_candidates.length > 0) {
                const targetCand = data.matched_candidates[0];
                showToast(`"${targetCand.title}" 9:16 olarak kırpılıyor ve altyazı giydiriliyor...`, 'info');
                const cardBtn = document.getElementById(`render-btn-${targetCand.id}`);
                if (cardBtn) {
                    await window.renderCandidateClip(targetCand.id, cardBtn);
                }
            } else {
                candidatesGrid.scrollIntoView({ behavior: 'smooth' });
            }

        } catch (err) {
            showToast('Arama Hatası: ' + err.message, 'error');
        } finally {
            if (activeBtn) {
                activeBtn.disabled = false;
                activeBtn.innerHTML = origHtml;
            }
        }
    }

    if (topicSearchBtn) {
        topicSearchBtn.addEventListener('click', () => executeTopicSearch(false));
    }
    if (topicSearchRenderBtn) {
        topicSearchRenderBtn.addEventListener('click', () => executeTopicSearch(true));
    }
    if (topicSearchInput) {
        topicSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                executeTopicSearch(false);
            }
        });
    }

    // Manuel Zaman Aralığı Aç/Kapa
    if (toggleManualCutBtn && manualCutFields) {
        toggleManualCutBtn.addEventListener('click', () => {
            const isHidden = manualCutFields.classList.contains('hidden');
            if (isHidden) {
                manualCutFields.classList.remove('hidden');
                if (manualCutArrow) manualCutArrow.classList.add('rotate-180');
            } else {
                manualCutFields.classList.add('hidden');
                if (manualCutArrow) manualCutArrow.classList.remove('rotate-180');
            }
        });
    }

    function parseTimeString(str) {
        if (!str) return 0;
        str = str.trim();
        if (str.includes(':')) {
            const parts = str.split(':');
            return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
        }
        return parseFloat(str) || 0;
    }

    // Manuel Aralığı Kırp ve Render Et
    if (manualCutBtn) {
        manualCutBtn.addEventListener('click', async () => {
            if (!currentProject) {
                showToast('Lütfen önce bir video analiz edin.', 'info');
                return;
            }

            const startVal = parseTimeString(manualStartInput ? manualStartInput.value : '');
            const endVal = parseTimeString(manualEndInput ? manualEndInput.value : '');

            if (endVal <= startVal) {
                showToast('Bitiş süresi başlangıçtan büyük olmalıdır (örn: 01:20 - 02:00).', 'error');
                return;
            }

            const origHtml = manualCutBtn.innerHTML;
            manualCutBtn.disabled = true;
            manualCutBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Kırpılıyor...</span>';

            try {
                const res = await fetchWithAuth('/api/custom-clip', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: currentProject.project_id,
                        start_time: startVal,
                        end_time: endVal
                    })
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || 'Özel aralık oluşturulamadı.');
                }

                const data = await res.json();
                currentProject.candidates = data.candidates;
                activeCandidateTab = 'custom';
                renderCandidates(currentProject.candidates);

                const newCand = data.custom_candidate;
                showToast(`Özel aralık (${Math.round(startVal)}s - ${Math.round(endVal)}s) oluşturuldu! 9:16 render ediliyor...`, 'info');

                const cardBtn = document.getElementById(`render-btn-${newCand.id}`);
                if (cardBtn) {
                    await window.renderCandidateClip(newCand.id, cardBtn);
                }

            } catch (err) {
                showToast('Manuel Kırpma Hatası: ' + err.message, 'error');
            } finally {
                manualCutBtn.disabled = false;
                manualCutBtn.innerHTML = origHtml;
            }
        });
    }

    // ==========================================
    // 11. GEÇMİŞ (HISTORY) & İŞLEM GÖREVLERİ YÖNETİMİ
    // ==========================================
    openHistoryBtn.addEventListener('click', () => {
        loadHistory();
        loadTrailersHistory();
        loadJobsHistory();
        historyDrawer.classList.remove('hidden');
    });

    closeHistoryBtn.addEventListener('click', () => {
        historyDrawer.classList.add('hidden');
    });

    window.switchHistoryTab = function(tab) {
        const btnProjects = document.getElementById('history-tab-projects');
        const btnTrailers = document.getElementById('history-tab-trailers');
        const btnTasks = document.getElementById('history-tab-tasks');
        const listProjects = document.getElementById('history-list');
        const listTrailers = document.getElementById('history-trailers-list');
        const listTasks = document.getElementById('history-tasks-list');

        const inactiveClass = 'flex-1 py-2 px-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition-all flex items-center justify-center gap-1';
        const activeIndigoClass = 'flex-1 py-2 px-1.5 rounded-lg font-semibold transition-all bg-indigo-600 text-white shadow-sm flex items-center justify-center gap-1';
        const activePurpleClass = 'flex-1 py-2 px-1.5 rounded-lg font-semibold transition-all bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-sm flex items-center justify-center gap-1';

        if (btnProjects) btnProjects.className = inactiveClass;
        if (btnTrailers) btnTrailers.className = inactiveClass;
        if (btnTasks) btnTasks.className = inactiveClass;

        if (listProjects) listProjects.classList.add('hidden');
        if (listTrailers) listTrailers.classList.add('hidden');
        if (listTasks) listTasks.classList.add('hidden');

        if (tab === 'projects') {
            if (btnProjects) btnProjects.className = activeIndigoClass;
            if (listProjects) listProjects.classList.remove('hidden');
            loadHistory();
        } else if (tab === 'trailers') {
            if (btnTrailers) btnTrailers.className = activePurpleClass;
            if (listTrailers) listTrailers.classList.remove('hidden');
            loadTrailersHistory();
        } else {
            if (btnTasks) btnTasks.className = activeIndigoClass;
            if (listTasks) listTasks.classList.remove('hidden');
            loadJobsHistory();
        }
    };

    window.loadTrailersHistory = async function() {
        const listTrailers = document.getElementById('history-trailers-list');
        const badgeTrailers = document.getElementById('history-tab-trailers-badge');
        if (!listTrailers) return;

        try {
            const res = await fetchWithAuth('/api/trailers');
            if (!res.ok) return;
            const trailers = await res.json();
            if (badgeTrailers) badgeTrailers.textContent = trailers.length;

            listTrailers.innerHTML = '';
            if (trailers.length === 0) {
                listTrailers.innerHTML = `
                    <div class="text-center py-8 space-y-2">
                        <i class="fa-solid fa-film text-slate-600 text-2xl"></i>
                        <p class="text-xs text-slate-500">Henüz oluşturulmuş akıllı fragman yok.</p>
                        <button type="button" onclick="switchStudioMode('trailer'); if (historyDrawer) historyDrawer.classList.add('hidden');" 
                            class="text-xs text-purple-400 hover:text-purple-300 underline font-medium">
                            Yeni Bir Fragman Oluşturun
                        </button>
                    </div>
                `;
                return;
            }

            trailers.forEach(t => {
                const item = document.createElement('div');
                item.className = 'bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2.5 hover:border-purple-500/50 hover:bg-slate-900/60 transition-all cursor-pointer group shadow-sm';
                item.onclick = () => window.openTrailerById(t.trailer_id);

                const sceneCount = (t.scenes || []).length;
                const durVal = t.trailer_duration || t.duration;
                const durStr = durVal ? `${Math.round(durVal)}s` : '';
                const formatBadge = t.aspect_ratio || '9:16';
                const origTitle = t.original_title || t.youtube_url || '';
                const displayTitle = t.trailer_title || t.video_title || 'Akıllı Fragman';
                const isCompleted = (t.status || 'completed') === 'completed';

                item.innerHTML = `
                    <div class="flex items-center gap-2.5">
                        <div class="w-11 h-11 rounded-lg bg-slate-900 border border-purple-800/40 flex-shrink-0 overflow-hidden flex items-center justify-center text-purple-400 relative shadow-sm">
                            ${t.thumbnail ? `<img src="${t.thumbnail}" class="w-full h-full object-cover">` : '<i class="fa-solid fa-film text-sm"></i>'}
                            <div class="absolute inset-0 bg-black/20 flex items-center justify-center">
                                <i class="fa-solid fa-play text-[10px] text-white/90 drop-shadow"></i>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <h4 class="text-xs font-semibold text-white truncate group-hover:text-purple-300 transition-colors" title="${escapeHtml(displayTitle)}">${escapeHtml(displayTitle)}</h4>
                            ${origTitle && origTitle !== displayTitle ? `
                                <p class="text-[10px] text-slate-400 truncate flex items-center gap-1 mt-0.5" title="${escapeHtml(origTitle)}">
                                    <i class="fa-brands fa-youtube text-red-500 text-[9px] flex-shrink-0"></i>
                                    <span class="truncate">${escapeHtml(origTitle)}</span>
                                </p>
                            ` : ''}
                            <p class="text-[9px] text-purple-300/80 font-mono mt-0.5">${t.created_at || ''} ${durStr ? `• ${durStr}` : ''}</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-between pt-1 border-t border-slate-850 text-[11px]">
                        <div class="flex items-center gap-1.5">
                            <span class="text-[9px] bg-purple-500/20 text-purple-300 border border-purple-500/30 px-1.5 py-0.2 rounded font-mono">${formatBadge}</span>
                            <span class="text-slate-400 text-[10px]">${sceneCount > 0 ? `${sceneCount} Bölüm` : 'Özet'}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-purple-400 font-semibold text-[11px] group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                                <i class="fa-solid fa-play text-[9px]"></i>
                                <span>${isCompleted ? 'İzle & Paylaş' : 'İlerlemeyi Gör'}</span>
                            </span>
                            <button type="button" onclick="event.stopPropagation(); deleteHistoryTrailer('${t.trailer_id}')" 
                                title="Fragmanı Sil" class="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 text-xs transition-colors">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
                listTrailers.appendChild(item);
            });
        } catch (e) {
            console.error('loadTrailersHistory error:', e);
        }
    };

    window.openTrailerById = async function(trailerId) {
        if (historyDrawer) historyDrawer.classList.add('hidden');
        window.switchStudioMode('trailer');

        const progressCard = document.getElementById('trailer-progress-card');
        const resultCard = document.getElementById('trailer-result-card');

        try {
            showToast('🎬 Fragman yükleniyor...', 'info');
            const res = await fetchWithAuth(`/api/trailer/${trailerId}`);
            if (!res.ok) throw new Error('Fragman bulunamadı.');
            const data = await res.json();
            activeTrailerData = data;
            localStorage.setItem('clipforge_active_trailer_id', trailerId);

            if (data.status === 'completed' && data.video_url) {
                if (progressCard) progressCard.classList.add('hidden');
                renderTrailerResult(data);
                showToast('✅ Akıllı fragman yüklendi!', 'success');
                setTimeout(() => {
                    const rc = document.getElementById('trailer-result-card');
                    if (rc) rc.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 150);
            } else if (data.status === 'failed') {
                if (progressCard) progressCard.classList.add('hidden');
                showToast('Fragman oluşturulamadı: ' + (data.error || data.message || ''), 'error');
            } else {
                // İşlem devam ediyor (queued, transcribing, analyzing, rendering)
                if (resultCard) resultCard.classList.add('hidden');
                if (progressCard) {
                    progressCard.classList.remove('hidden');
                    updateTrailerProgress(data.progress || 15, data.message || 'Fragman hazırlanıyor...');
                    setTimeout(() => progressCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);
                }
                showToast('⏳ Fragman işlemi devam ediyor, ilerleme izleniyor...', 'info');
                startTrailerPolling(trailerId);
            }
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    window.deleteHistoryTrailer = async function(trailerId) {
        if (!confirm('Bu fragmanı ve videosunu silmek istediğinize emin misiniz?')) return;
        try {
            const res = await fetchWithAuth(`/api/trailers/${trailerId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Silinemedi.');
            showToast('Fragman silindi.', 'success');
            loadTrailersHistory();
            loadJobsHistory();
            if (activeTrailerData && activeTrailerData.trailer_id === trailerId) {
                activeTrailerData = null;
                localStorage.removeItem('clipforge_active_trailer_id');
                const resultCard = document.getElementById('trailer-result-card');
                if (resultCard) resultCard.classList.add('hidden');
            }
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    async function loadHistory() {
        try {
            const res = await fetchWithAuth('/api/history');
            if (!res.ok) return;
            const projects = await res.json();

            historyBadge.textContent = projects.length;
            const projectsBadge = document.getElementById('history-tab-projects-badge');
            if (projectsBadge) projectsBadge.textContent = projects.length;

            historyList.innerHTML = '';

            if (projects.length === 0) {
                historyList.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Henüz kayıtlı proje yok.</p>';
                return;
            }

            projects.forEach(p => {
                const item = document.createElement('div');
                item.className = 'bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2.5 hover:border-indigo-500/60 hover:bg-slate-900/60 transition-all cursor-pointer group shadow-sm';
                item.onclick = () => selectHistoryProject(p.project_id);
                
                const renderedCount = (p.rendered_clips || []).length;
                const candCount = (p.candidates || []).length;

                item.innerHTML = `
                    <div class="flex items-center gap-2.5">
                        <div class="w-10 h-10 rounded-lg bg-slate-900 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
                            ${p.thumbnail ? `<img src="${p.thumbnail}" class="w-full h-full object-cover">` : '<i class="fa-solid fa-film text-slate-600 text-xs"></i>'}
                        </div>
                        <div class="flex-1 min-w-0">
                            <h4 class="text-xs font-semibold text-white truncate group-hover:text-indigo-300 transition-colors">${escapeHtml(p.title)}</h4>
                            <p class="text-[10px] text-slate-400">${p.created_at || ''} • ${Math.round(p.duration)}s</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-between pt-1 border-t border-slate-850 text-[11px]">
                        <span class="text-slate-400 text-[10px]">${candCount} Aday / <strong class="text-emerald-400">${renderedCount} Klip</strong></span>
                        <div class="flex items-center gap-2">
                            <span class="text-indigo-400 font-semibold text-[11px] group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                                <span>Aç</span>
                                <i class="fa-solid fa-chevron-right text-[10px]"></i>
                            </span>
                            <button type="button" onclick="event.stopPropagation(); deleteHistoryProject('${p.project_id}')" 
                                title="Projeyi Sil" class="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 text-xs transition-colors">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;

                historyList.appendChild(item);
            });

        } catch (e) {
            console.error('History load error:', e);
        }
    }

    window.loadJobsHistory = async function() {
        const listTasks = document.getElementById('history-tasks-list');
        const tasksBadge = document.getElementById('history-tab-tasks-badge');
        if (!listTasks) return;

        try {
            const res = await fetchWithAuth('/api/jobs');
            if (!res.ok) return;
            const jobs = await res.json();
            if (tasksBadge) tasksBadge.textContent = jobs.length;

            listTasks.innerHTML = '';
            if (jobs.length === 0) {
                listTasks.innerHTML = '<p class="text-xs text-slate-500 text-center py-6">Henüz işlem geçmişi bulunmuyor.</p>';
                return;
            }

            jobs.forEach(task => {
                const item = document.createElement('div');
                const st = task.status || 'queued';
                
                let badgeClass = 'border-slate-700 bg-slate-800 text-slate-400';
                let badgeLabel = 'Sırada';
                let badgeIcon = '<i class="fa-solid fa-clock text-[9px]"></i>';

                if (task.is_trailer) {
                    if (st === 'completed') {
                        badgeClass = 'border-purple-500/40 bg-purple-500/20 text-purple-300';
                        badgeLabel = 'Fragman Hazır';
                        badgeIcon = '<i class="fa-solid fa-film text-[9px]"></i>';
                    } else if (st === 'failed') {
                        badgeClass = 'border-rose-500/40 bg-rose-500/15 text-rose-300';
                        badgeLabel = 'Başarısız';
                        badgeIcon = '<i class="fa-solid fa-circle-xmark text-[9px]"></i>';
                    } else if (st === 'rendering') {
                        badgeClass = 'border-pink-500/40 bg-pink-500/15 text-pink-300 animate-pulse';
                        badgeLabel = `Render (%${task.progress || 65})`;
                        badgeIcon = '<i class="fa-solid fa-scissors text-[9px]"></i>';
                    } else if (st === 'analyzing') {
                        badgeClass = 'border-purple-500/40 bg-purple-500/15 text-purple-300 animate-pulse';
                        badgeLabel = `Analiz (%${task.progress || 45})`;
                        badgeIcon = '<i class="fa-solid fa-wand-magic-sparkles text-[9px]"></i>';
                    } else if (st === 'transcribing') {
                        badgeClass = 'border-blue-500/40 bg-blue-500/15 text-blue-300 animate-pulse';
                        badgeLabel = `Deşifre (%${task.progress || 25})`;
                        badgeIcon = '<i class="fa-solid fa-microphone text-[9px]"></i>';
                    } else {
                        badgeClass = 'border-slate-700 bg-slate-800 text-slate-400 animate-pulse';
                        badgeLabel = `Sırada (%${task.progress || 5})`;
                        badgeIcon = '<i class="fa-solid fa-clock text-[9px]"></i>';
                    }
                } else if (st === 'completed') {
                    badgeClass = 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300';
                    badgeLabel = 'Tamamlandı';
                    badgeIcon = '<i class="fa-solid fa-circle-check text-[9px]"></i>';
                } else if (st === 'downloading') {
                    badgeClass = 'border-blue-500/40 bg-blue-500/15 text-blue-300 animate-pulse';
                    badgeLabel = 'İndiriliyor';
                    badgeIcon = '<i class="fa-solid fa-arrow-down text-[9px]"></i>';
                } else if (st === 'transcribing') {
                    badgeClass = 'border-purple-500/40 bg-purple-500/15 text-purple-300 animate-pulse';
                    badgeLabel = `Deşifre (%${task.progress || 25})`;
                    badgeIcon = '<i class="fa-solid fa-microphone text-[9px]"></i>';
                } else if (st === 'scoring') {
                    badgeClass = 'border-amber-500/40 bg-amber-500/15 text-amber-300 animate-pulse';
                    badgeLabel = 'Puanlanıyor';
                    badgeIcon = '<i class="fa-solid fa-wand-magic-sparkles text-[9px]"></i>';
                } else if (st === 'interrupted') {
                    badgeClass = 'border-amber-500/50 bg-amber-500/20 text-amber-300';
                    badgeLabel = 'Kesintiye Uğradı';
                    badgeIcon = '<i class="fa-solid fa-triangle-exclamation text-[9px]"></i>';
                } else if (st === 'failed') {
                    badgeClass = 'border-rose-500/40 bg-rose-500/15 text-rose-300';
                    badgeLabel = 'Başarısız';
                    badgeIcon = '<i class="fa-solid fa-circle-xmark text-[9px]"></i>';
                } else if (st === 'cancelled') {
                    badgeClass = 'border-slate-700 bg-slate-800 text-slate-400';
                    badgeLabel = 'İptal Edildi';
                    badgeIcon = '<i class="fa-solid fa-ban text-[9px]"></i>';
                }

                const isActive = ['queued', 'downloading', 'transcribing', 'scoring', 'analyzing', 'rendering'].includes(st);
                const canRetry = ['interrupted', 'failed', 'cancelled'].includes(st);

                const dispTitle = task.original_title || task.video_title || task.trailer_title || task.url || 'Akıllı Fragman';
                const hasDiffTitle = task.is_trailer && task.trailer_title && task.original_title && task.trailer_title !== task.original_title;

                item.className = `bg-slate-950/90 border ${task.is_trailer ? 'border-purple-500/40 shadow-sm shadow-purple-500/10' : (isActive ? 'border-indigo-500/50 shadow-md shadow-indigo-500/10' : (st === 'interrupted' ? 'border-amber-500/40' : 'border-slate-800'))} rounded-xl p-3 space-y-2.5 shadow-sm`;
                
                item.innerHTML = `
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-2.5 min-w-0 flex-1">
                            <div class="w-9 h-9 rounded-lg bg-slate-900 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
                                ${task.thumbnail ? `<img src="${task.thumbnail}" class="w-full h-full object-cover">` : (task.is_trailer ? '<i class="fa-solid fa-film text-purple-400 text-xs"></i>' : '<i class="fa-brands fa-youtube text-red-500 text-xs"></i>')}
                            </div>
                            <div class="min-w-0 flex-1">
                                <h4 class="text-xs font-semibold text-white truncate" title="${escapeHtml(dispTitle)}">
                                    ${escapeHtml(dispTitle)}
                                </h4>
                                ${hasDiffTitle ? `
                                    <p class="text-[10px] text-purple-300/80 truncate flex items-center gap-1 mt-0.5" title="${escapeHtml(task.trailer_title)}">
                                        <i class="fa-solid fa-sparkles text-[8px] text-purple-400"></i>
                                        <span class="truncate">${escapeHtml(task.trailer_title)}</span>
                                    </p>
                                ` : ''}
                                <p class="text-[10px] text-slate-400">
                                    ${task.created_at || ''} ${task.duration ? `• ${Math.round(task.duration)}s` : ''}
                                </p>
                            </div>
                        </div>
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClass} flex items-center gap-1 flex-shrink-0">
                            ${badgeIcon} <span>${badgeLabel}</span>
                        </span>
                    </div>

                    <div class="text-[11px] text-slate-300 bg-slate-900/80 px-2.5 py-1.5 rounded-lg border border-slate-850">
                        <div class="line-clamp-1">${escapeHtml(task.message || task.error || 'İşlem kaydı')}</div>
                        ${task.sub_status ? `<div class="text-[10px] text-indigo-300 italic line-clamp-1 mt-0.5">${escapeHtml(task.sub_status)}</div>` : ''}
                    </div>

                    <div class="flex items-center justify-between pt-1 border-t border-slate-850 text-xs">
                        <div class="flex items-center gap-2">
                            ${task.is_trailer ? `
                                ${st === 'completed' ? `
                                    <button type="button" onclick="openTrailerById('${task.trailer_id}')" 
                                        class="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white text-[11px] font-semibold py-1 px-2.5 rounded-lg flex items-center gap-1 shadow-sm transition-all cursor-pointer">
                                        <i class="fa-solid fa-play text-[10px]"></i> <span>Fragmanı Aç</span>
                                    </button>
                                ` : `
                                    <button type="button" onclick="openTrailerById('${task.trailer_id}')" 
                                        class="bg-purple-600 hover:bg-purple-500 text-white text-[11px] font-semibold py-1 px-2.5 rounded-lg flex items-center gap-1 shadow-sm transition-all cursor-pointer">
                                        <i class="fa-solid fa-eye text-[10px]"></i> <span>İlerlemeyi Gör (%${task.progress || 0})</span>
                                    </button>
                                `}
                            ` : `
                                ${isActive ? `
                                    <button type="button" onclick="attachToRunningJob('${task.job_id}')" 
                                        class="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold py-1 px-2.5 rounded-lg flex items-center gap-1 transition-all">
                                        <i class="fa-solid fa-eye text-[10px]"></i> <span>İlerlemeyi Gör</span>
                                    </button>
                                ` : ''}
                                ${canRetry ? `
                                    <button type="button" onclick="retryJobTask('${task.job_id}')" 
                                        class="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-[11px] font-semibold py-1 px-2.5 rounded-lg flex items-center gap-1 shadow-sm transition-all">
                                        <i class="fa-solid fa-rotate-right text-[10px]"></i> <span>Tekrar Başlat</span>
                                    </button>
                                ` : ''}
                                ${st === 'completed' ? `
                                    <button type="button" onclick="selectHistoryProject('${task.job_id}')" 
                                        class="bg-slate-800 hover:bg-slate-750 text-slate-200 text-[11px] font-semibold py-1 px-2.5 rounded-lg flex items-center gap-1 transition-all">
                                        <i class="fa-solid fa-folder-open text-[10px] text-indigo-400"></i> <span>Projeyi Aç</span>
                                    </button>
                                ` : ''}
                            `}
                        </div>
                        <button type="button" onclick="${task.is_trailer ? `deleteHistoryTrailer('${task.trailer_id}')` : `deleteJobTask('${task.job_id}', this)`}" 
                            title="Kaydı Sil" class="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 text-xs transition-colors">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `;

                listTasks.appendChild(item);
            });
        } catch (e) {
            console.error('Jobs load error:', e);
        }
    };

    window.attachToRunningJob = function(jobId) {
        if (!jobId) return;
        localStorage.setItem('clipforge_active_job_id', jobId);
        activeJobId = jobId;
        if (historyDrawer) historyDrawer.classList.add('hidden');
        restoreActiveJobIfNeeded();
        startAnalyzePolling(jobId);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.retryJobTask = async function(jobId) {
        if (!confirm('Bu videonun analizini yeniden başlatmak istiyor musunuz?')) return;
        try {
            const res = await fetchWithAuth(`/api/jobs/${jobId}/retry`, { method: 'POST' });
            if (!res.ok) throw new Error('Yeniden başlatılamadı.');
            const data = await res.json();
            if (historyDrawer) historyDrawer.classList.add('hidden');
            activeJobId = data.job_id;
            localStorage.setItem('clipforge_active_job_id', data.job_id);

            progressContainer.classList.remove('hidden');
            progressSpinner.classList.remove('hidden');
            progressSuccessIcon.classList.add('hidden');
            candidatesContainer.classList.add('hidden');
            renderedContainer.classList.add('hidden');
            projectHeader.classList.add('hidden');

            updateProgress(5, 'İşlem yeniden başlatılıyor...');
            startAnalyzePolling(data.job_id);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            showToast('Analiz işlemi yeniden başlatıldı!', 'info');
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    window.deleteJobTask = async function(jobId, btn) {
        try {
            const res = await fetchWithAuth(`/api/jobs/${jobId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Silinemedi.');
            showToast('İşlem kaydı silindi.', 'success');
            loadJobsHistory();
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    window.selectHistoryProject = async function(projectId) {
        try {
            const res = await fetchWithAuth(`/api/history/${projectId}`);
            if (!res.ok) throw new Error('Proje açılamadı.');
            const p = await res.json();
            loadProjectFromData(projectId, p);
            if (historyDrawer) historyDrawer.classList.add('hidden');
            showToast(`"${p.title}" projesi yüklendi.`, 'info');
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    window.deleteHistoryProject = async function(projectId) {
        if (!confirm('Bu projeyi ve üretilen tüm videoları kalıcı olarak silmek istediğinize emin misiniz?')) {
            return;
        }

        try {
            const res = await fetchWithAuth(`/api/history/${projectId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Proje silinemedi.');
            showToast('Proje başarıyla silindi.', 'success');
            loadHistory();

            if (currentProject && currentProject.project_id === projectId) {
                currentProject = null;
                projectHeader.classList.add('hidden');
                candidatesContainer.classList.add('hidden');
                renderedContainer.classList.add('hidden');
            }
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    window.deleteSingleClip = async function(clipId) {
        if (!currentProject) return;
        if (!confirm('Bu klibin video dosyasını silmek istediğinize emin misiniz?')) return;

        try {
            const res = await fetchWithAuth(`/api/history/${currentProject.project_id}/clips/${clipId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Klip silinemedi.');

            // ID eşleşmesinde esnek filtreleme
            currentProject.rendered_clips = (currentProject.rendered_clips || []).filter(c => {
                const cid = String(c.id);
                const target = String(clipId);
                return cid !== target && !cid.endsWith('_' + target) && !target.endsWith('_' + cid);
            });

            for (let c of (currentProject.candidates || [])) {
                const cid = String(c.id);
                const target = String(clipId);
                if (cid === target || cid.endsWith('_' + target) || target.endsWith('_' + cid)) {
                    c.is_rendered = false;
                    c.video_filename = null;
                    c.video_url = null;
                }
            }

            renderFinishedClips(currentProject.rendered_clips);
            renderCandidates(currentProject.candidates);
            loadHistory();

            // Eğer hiç hazır klip kalmadıysa otomatik olarak Aday Kesitler sekmesine geç
            if (currentProject.rendered_clips.length === 0) {
                window.switchMainView('candidates');
            }

            showToast('Klip başarıyla silindi.', 'success');
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    if (scrollRenderedBtn) {
        scrollRenderedBtn.addEventListener('click', () => {
            if (renderedContainer) renderedContainer.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // ==========================================
    // 12. YARDIMCI METODLAR
    // ==========================================
    window.pauseOtherVideos = function(currentVideo) {
        const allVideos = document.querySelectorAll('video');
        allVideos.forEach(v => {
            if (v !== currentVideo && !v.paused) v.pause();
        });
    };

    function downloadFallback(url, filename) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function formatSec(seconds) {
        const s = Math.round(seconds || 0);
        const hrs = Math.floor(s / 3600);
        const mins = Math.floor((s % 3600) / 60);
        const rem = s % 60;
        if (hrs > 0) {
            return `${hrs}:${mins < 10 ? '0' : ''}${mins}:${rem < 10 ? '0' : ''}${rem}`;
        }
        return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
    }

    function formatSeconds(seconds) {
        return formatSec(seconds);
    }
    window.formatSec = formatSec;
    window.formatSeconds = formatSec;

    function isMobile() {
        return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    }

    function showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        const toastIcon = document.getElementById('toast-icon');

        toastMessage.textContent = message;
        if (type === 'error') {
            toastIcon.className = 'fa-solid fa-triangle-exclamation text-rose-400 text-base';
            toast.className = 'fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-md bg-slate-900 border border-rose-800/80 text-white px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 z-[110] flex items-center gap-3 text-xs sm:text-sm translate-y-0 opacity-100';
        } else if (type === 'info') {
            toastIcon.className = 'fa-solid fa-circle-info text-indigo-400 text-base';
            toast.className = 'fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-md bg-slate-900 border border-indigo-800/80 text-white px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 z-[110] flex items-center gap-3 text-xs sm:text-sm translate-y-0 opacity-100';
        } else {
            toastIcon.className = 'fa-solid fa-circle-check text-emerald-400 text-base';
            toast.className = 'fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-md bg-slate-900 border border-emerald-800/80 text-white px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 z-[110] flex items-center gap-3 text-xs sm:text-sm translate-y-0 opacity-100';
        }

        setTimeout(() => {
            toast.classList.add('translate-y-24', 'opacity-0');
        }, 3500);
    }

    function escapeHtml(string) {
        if (!string) return '';
        return String(string)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ==========================================
    // 13. TÜMÜNÜ SIRAYLA RENDER ETME
    // ==========================================
    const renderAllCandidatesBtn = document.getElementById('render-all-candidates-btn');
    if (renderAllCandidatesBtn) {
        renderAllCandidatesBtn.addEventListener('click', async () => {
            if (!currentProject || !currentProject.candidates || currentProject.candidates.length === 0) return;

            const unrendered = currentProject.candidates.filter(c => !c.is_rendered);
            if (unrendered.length === 0) {
                showToast('Tüm adaylar zaten render edilmiş!', 'info');
                return;
            }

            const origHtml = renderAllCandidatesBtn.innerHTML;
            renderAllCandidatesBtn.disabled = true;
            
            showToast(`${unrendered.length} adet klip sırayla render ediliyor...`, 'info');

            for (let i = 0; i < unrendered.length; i++) {
                const cand = unrendered[i];
                renderAllCandidatesBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Render: ${i + 1}/${unrendered.length}</span>`;
                
                const btn = document.getElementById(`render-btn-${cand.id}`);
                if (btn) {
                    await window.renderCandidateClip(cand.id, btn);
                }
            }

            renderAllCandidatesBtn.disabled = false;
            renderAllCandidatesBtn.innerHTML = origHtml;
            showToast('Tüm seçili kliplerin render işlemi tamamlandı!', 'success');
        });
    }

    window.toggleSafeZone = function(clipId, btn) {
        const card = document.getElementById(`rendered-card-${clipId}`);
        if (!card) return;
        const overlay = card.querySelector('.safe-zone-overlay');
        if (overlay) {
            overlay.classList.toggle('hidden');
            btn.classList.toggle('bg-indigo-600/30');
            btn.classList.toggle('text-indigo-200');
            btn.classList.toggle('border-indigo-500/40');
        }
    };

    // ==========================================
    // 14. PWA (PROGRESSIVE WEB APP) YÖNETİMİ
    // ==========================================
    let deferredInstallPrompt = null;
    const pwaInstallBtn = document.getElementById('pwa-install-btn');
    const pwaInstallBanner = document.getElementById('pwa-install-banner');
    const pwaBannerInstallBtn = document.getElementById('pwa-banner-install-btn');
    const pwaBannerCloseBtn = document.getElementById('pwa-banner-close-btn');
    const iosPwaModal = document.getElementById('ios-pwa-modal');
    const closeIosModalBtn = document.getElementById('close-ios-modal-btn');
    const dismissIosModalBtn = document.getElementById('dismiss-ios-modal-btn');

    // Service Worker Kaydı (PWA Installability Criteria)
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then(reg => console.log('ServiceWorker registered with scope:', reg.scope))
                .catch(err => console.warn('ServiceWorker registration error:', err));
        });
    }

    // Cihazın Standalone (PWA) modunda olup olmadığını kontrol et
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

    // iOS Safari tespiti
    const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());

    if (!isStandalone) {
        // Android / Chromium tarayıcılarda kurulum istemi yakalama
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredInstallPrompt = e;

            if (pwaInstallBtn) pwaInstallBtn.classList.remove('hidden');

            const isBannerDismissed = localStorage.getItem('clipforge_pwa_banner_dismissed');
            if (pwaInstallBanner && !isBannerDismissed) {
                pwaInstallBanner.classList.remove('hidden');
            }
        });

        // iOS cihazlarda kurulum butonu ve banner'ı görünür kıl
        if (isIos) {
            if (pwaInstallBtn) pwaInstallBtn.classList.remove('hidden');
            const isBannerDismissed = localStorage.getItem('clipforge_pwa_banner_dismissed');
            if (pwaInstallBanner && !isBannerDismissed) {
                pwaInstallBanner.classList.remove('hidden');
            }
        }
    }

    async function handleInstallPrompt() {
        if (isIos) {
            if (iosPwaModal) iosPwaModal.classList.remove('hidden');
            return;
        }

        if (deferredInstallPrompt) {
            deferredInstallPrompt.prompt();
            const { outcome } = await deferredInstallPrompt.userChoice;
            if (outcome === 'accepted') {
                showToast('ClipForge AI uygulaması başarıyla yüklendi!', 'success');
                if (pwaInstallBtn) pwaInstallBtn.classList.add('hidden');
                if (pwaInstallBanner) pwaInstallBanner.classList.add('hidden');
            }
            deferredInstallPrompt = null;
        } else {
            showToast('Tarayıcınızın menüsünden "Uygulamayı Yükle" veya "Ana Ekrana Ekle" seçeneğini kullanabilirsiniz.', 'info');
        }
    }

    if (pwaInstallBtn) pwaInstallBtn.addEventListener('click', handleInstallPrompt);
    if (pwaBannerInstallBtn) pwaBannerInstallBtn.addEventListener('click', handleInstallPrompt);

    if (pwaBannerCloseBtn) {
        pwaBannerCloseBtn.addEventListener('click', () => {
            if (pwaInstallBanner) pwaInstallBanner.classList.add('hidden');
            localStorage.setItem('clipforge_pwa_banner_dismissed', 'true');
        });
    }

    if (closeIosModalBtn) {
        closeIosModalBtn.addEventListener('click', () => {
            if (iosPwaModal) iosPwaModal.classList.add('hidden');
        });
    }
    if (dismissIosModalBtn) {
        dismissIosModalBtn.addEventListener('click', () => {
            if (iosPwaModal) iosPwaModal.classList.add('hidden');
        });
    }

    // ==========================================
    // AKILLI FRAGMAN & ÖZET STÜDYOSU (TRAILER)
    // ==========================================
    let currentTrailerSourceMode = 'url'; // 'url' (varsayılan) | 'project'
    let trailerPollInterval = null;
    let activeTrailerData = null;

    window.switchStudioMode = function(mode) {
        const shortsTab = document.getElementById('tab-mode-shorts');
        const trailerTab = document.getElementById('tab-mode-trailer');
        const shortsView = document.getElementById('shorts-studio-view');
        const trailerView = document.getElementById('trailer-studio-view');

        if (mode === 'trailer') {
            if (shortsTab) {
                shortsTab.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all text-slate-400 hover:text-white cursor-pointer';
            }
            if (trailerTab) {
                trailerTab.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-md shadow-purple-500/20 cursor-pointer';
            }
            if (shortsView) shortsView.classList.add('hidden');
            if (trailerView) trailerView.classList.remove('hidden');

            const navBtnTrailer = document.getElementById('nav-btn-trailer');
            const navBtnCand = document.getElementById('nav-btn-candidates');
            const navBtnRend = document.getElementById('nav-btn-rendered');
            if (navBtnTrailer) navBtnTrailer.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-purple-400 font-bold transition-all active:scale-95';
            if (navBtnCand) navBtnCand.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95';
            if (navBtnRend) navBtnRend.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95 relative';

            // Eğer ana arayüzde bir YouTube linki girilmişse fragman linkine otomatik aktar
            const trailerUrlInput = document.getElementById('trailer-video-url');
            const mainUrlInput = document.getElementById('youtube-url');
            if (trailerUrlInput && !trailerUrlInput.value.trim() && mainUrlInput && mainUrlInput.value.trim()) {
                trailerUrlInput.value = mainUrlInput.value.trim();
            }

            loadTrailerProjects();

            // Eğer aktif bir fragman gösterilmiyorsa son üretilen fragmanı otomatik yükle
            const resultCard = document.getElementById('trailer-result-card');
            if (resultCard && resultCard.classList.contains('hidden')) {
                restoreLastTrailer();
            }
        } else {
            if (shortsTab) {
                shortsTab.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-500/20 cursor-pointer';
            }
            if (trailerTab) {
                trailerTab.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all text-slate-400 hover:text-white cursor-pointer';
            }
            if (shortsView) shortsView.classList.remove('hidden');
            if (trailerView) trailerView.classList.add('hidden');

            const navBtnTrailer = document.getElementById('nav-btn-trailer');
            if (navBtnTrailer) navBtnTrailer.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-slate-400 hover:text-white font-medium transition-all active:scale-95';
            if (currentMainView === 'rendered' && navBtnRendered) {
                navBtnRendered.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-emerald-400 font-bold transition-all active:scale-95 relative';
            } else if (navBtnCandidates) {
                navBtnCandidates.className = 'flex-1 py-1 flex flex-col items-center gap-1 text-indigo-400 font-bold transition-all active:scale-95';
            }
        }
    };

    async function restoreLastTrailer() {
        try {
            const savedId = localStorage.getItem('clipforge_active_trailer_id');
            if (savedId) {
                const res = await fetchWithAuth(`/api/trailer/${savedId}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.status === 'completed' && data.video_url) {
                        activeTrailerData = data;
                        renderTrailerResult(data);
                        return;
                    }
                }
            }

            // Eğer localStorage'da yoksa en son tamamlanan fragmanı getir
            const listRes = await fetchWithAuth('/api/trailers');
            if (listRes.ok) {
                const list = await listRes.json();
                const completed = list.find(t => t.status === 'completed' && t.video_url);
                if (completed) {
                    activeTrailerData = completed;
                    localStorage.setItem('clipforge_active_trailer_id', completed.trailer_id);
                    renderTrailerResult(completed);
                }
            }
        } catch (e) {
            console.warn('restoreLastTrailer error:', e);
        }
    }

    window.pasteToTrailerUrl = async function() {
        const input = document.getElementById('trailer-video-url');
        if (!input) return;
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const text = await navigator.clipboard.readText();
                if (text && (text.includes('youtube.com') || text.includes('youtu.be') || text.startsWith('http'))) {
                    input.value = text.trim();
                    input.focus();
                    showToast('YouTube bağlantısı yapıştırıldı!', 'info');
                    return;
                }
            }
        } catch (e) {
            console.warn('Clipboard read failed:', e);
        }
        const mainUrlInput = document.getElementById('youtube-url');
        if (mainUrlInput && mainUrlInput.value.trim()) {
            input.value = mainUrlInput.value.trim();
            showToast('Ana ekrandaki YouTube bağlantısı aktarıldı!', 'info');
        } else {
            input.focus();
        }
    };

    window.switchTrailerSourceMode = function(mode) {
        currentTrailerSourceMode = mode;
        const projectBtn = document.getElementById('trailer-src-project-btn');
        const urlBtn = document.getElementById('trailer-src-url-btn');
        const projectContainer = document.getElementById('trailer-project-select-container');
        const urlContainer = document.getElementById('trailer-url-input-container');

        if (mode === 'project') {
            if (projectBtn) projectBtn.className = 'py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all bg-purple-600/30 text-purple-300 border border-purple-500/40 cursor-pointer';
            if (urlBtn) urlBtn.className = 'py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all text-slate-400 hover:text-white cursor-pointer';
            if (projectContainer) projectContainer.classList.remove('hidden');
            if (urlContainer) urlContainer.classList.add('hidden');
        } else {
            if (urlBtn) urlBtn.className = 'py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all bg-purple-600/30 text-purple-300 border border-purple-500/40 cursor-pointer';
            if (projectBtn) projectBtn.className = 'py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all text-slate-400 hover:text-white cursor-pointer';
            if (projectContainer) projectContainer.classList.add('hidden');
            if (urlContainer) urlContainer.classList.remove('hidden');
            const urlInput = document.getElementById('trailer-video-url');
            if (urlInput) urlInput.focus();
        }
    };

    async function loadTrailerProjects() {
        const select = document.getElementById('trailer-project-select');
        if (!select) return;

        try {
            const res = await fetchWithAuth('/api/history');
            if (!res.ok) throw new Error('Projeler alınamadı.');
            const projects = await res.json();

            if (!projects || projects.length === 0) {
                select.innerHTML = '<option value="">Henüz tamamlanmış proje bulunamadı</option>';
                return;
            }

            select.innerHTML = projects.map(p => `
                <option value="${p.project_id}">
                    ${escapeHtml(p.title || 'İsimsiz Proje')} (${formatSec(p.duration || 0)})
                </option>
            `).join('');

            // Eğer şu an açık olan bir proje varsa onu varsayılan seç
            if (currentProject && currentProject.project_id) {
                select.value = currentProject.project_id;
            }
        } catch (e) {
            console.error('loadTrailerProjects error:', e);
        }
    }

    window.onTrailerDurationChange = function(val) {
        const customBox = document.getElementById('trailer-custom-duration-box');
        const badge = document.getElementById('trailer-duration-badge');

        if (val === 'custom') {
            if (customBox) customBox.classList.remove('hidden');
            if (badge) badge.textContent = 'Özel';
        } else {
            if (customBox) customBox.classList.add('hidden');
            const sec = parseInt(val) || 60;
            if (badge) {
                if (sec < 60) badge.textContent = `${sec} sn`;
                else badge.textContent = `${Math.round(sec / 60)} dk`;
            }
        }
    };

    window.onTrailerAspectChange = function(val) {
        const cropBox = document.getElementById('trailer-crop-mode-container');
        if (cropBox) {
            if (val === '16:9') {
                cropBox.classList.add('hidden');
            } else {
                cropBox.classList.remove('hidden');
            }
        }
    };

    window.startTrailerGeneration = async function() {
        const durationSelect = document.getElementById('trailer-target-duration');
        const aspectSelect = document.getElementById('trailer-aspect-ratio');
        const cropModeSelect = document.getElementById('trailer-crop-mode');
        const styleSelect = document.getElementById('trailer-style');
        const submitBtn = document.getElementById('submit-trailer-btn');

        let targetDuration = 60;
        const durVal = durationSelect ? durationSelect.value : '60';
        if (durVal === 'custom') {
            const customInput = document.getElementById('trailer-custom-duration');
            const parsed = parseInt(customInput ? customInput.value : '');
            if (isNaN(parsed) || parsed < 15 || parsed > 1800) {
                showToast('Lütfen 15 ile 1800 saniye (30 dk) arasında geçerli bir süre girin.', 'error');
                return;
            }
            targetDuration = parsed;
        } else {
            targetDuration = parseInt(durVal) || 60;
        }

        const cropMode = cropModeSelect ? cropModeSelect.value : 'blur_background';
        let payload = {
            target_duration: targetDuration,
            aspect_ratio: aspectSelect ? aspectSelect.value : '9:16',
            crop_mode: cropMode,
            style: styleSelect ? styleSelect.value : 'cinematic'
        };

        if (currentTrailerSourceMode === 'project') {
            const projectSelect = document.getElementById('trailer-project-select');
            const projectId = projectSelect ? projectSelect.value : '';
            if (!projectId) {
                showToast('Lütfen fragmanı oluşturulacak bir proje seçin.', 'error');
                return;
            }
            payload.project_id = projectId;
        } else {
            const urlInput = document.getElementById('trailer-video-url');
            const url = urlInput ? urlInput.value.trim() : '';
            if (!url) {
                showToast('Lütfen geçerli bir YouTube video linki girin.', 'error');
                return;
            }
            payload.url = url;
        }

        const progressCard = document.getElementById('trailer-progress-card');
        const resultCard = document.getElementById('trailer-result-card');

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
        if (progressCard) progressCard.classList.remove('hidden');
        if (resultCard) resultCard.classList.add('hidden');

        updateTrailerProgress(10, 'Yapay zeka fragman sürecini başlatıyor...');

        try {
            const res = await fetchWithAuth('/api/trailer/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Fragman başlatılamadı.');
            }

            const data = await res.json();
            showToast('Akıllı fragman oluşturma süreci başladı!', 'info');
            startTrailerPolling(data.trailer_id);
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
            if (progressCard) progressCard.classList.add('hidden');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
    };

    function updateTrailerProgress(pct, msg) {
        const pctEl = document.getElementById('trailer-progress-pct');
        const barEl = document.getElementById('trailer-progress-bar');
        const msgEl = document.getElementById('trailer-progress-msg');

        if (pctEl) pctEl.innerText = `${pct}%`;
        if (barEl) barEl.style.width = `${pct}%`;
        if (msgEl) msgEl.innerText = msg;
    }

    function startTrailerPolling(trailerId) {
        if (trailerPollInterval) clearInterval(trailerPollInterval);

        trailerPollInterval = setInterval(async () => {
            try {
                const res = await fetchWithAuth(`/api/trailer/${trailerId}`);
                if (!res.ok) return;

                const data = await res.json();
                activeTrailerData = data;
                updateTrailerProgress(data.progress || 50, data.message || 'İşlem sürüyor...');

                if (data.status === 'completed') {
                    clearInterval(trailerPollInterval);
                    trailerPollInterval = null;
                    showToast('🎉 Akıllı fragman başarıyla tamamlandı!', 'success');
                    renderTrailerResult(data);
                } else if (data.status === 'failed') {
                    clearInterval(trailerPollInterval);
                    trailerPollInterval = null;
                    showToast('Fragman oluşturulamadı: ' + (data.error || data.message), 'error');
                    const progressCard = document.getElementById('trailer-progress-card');
                    if (progressCard) progressCard.classList.add('hidden');
                    const submitBtn = document.getElementById('submit-trailer-btn');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    }
                }
            } catch (e) {
                console.error('Trailer polling error:', e);
            }
        }, 1500);
    }

    function renderTrailerResult(data) {
        if (data && data.trailer_id) {
            localStorage.setItem('clipforge_active_trailer_id', data.trailer_id);
        }

        const progressCard = document.getElementById('trailer-progress-card');
        const resultCard = document.getElementById('trailer-result-card');
        const submitBtn = document.getElementById('submit-trailer-btn');
        const videoPlayer = document.getElementById('trailer-video-player');
        const titleEl = document.getElementById('trailer-result-title');
        const durationEl = document.getElementById('trailer-result-duration');
        const scenesListEl = document.getElementById('trailer-scenes-list');
        const downloadBtn = document.getElementById('trailer-download-btn');
        const shareBtn = document.getElementById('trailer-share-btn');

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        if (progressCard) progressCard.classList.add('hidden');
        if (resultCard) {
            resultCard.classList.remove('hidden');
            setTimeout(() => {
                resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }

        // Düzenlenebilir Alanları Doldur (Reels / TikTok Başlık, Açıklama ve Etiketler)
        const finalTitleInput = document.getElementById('trailer-final-title');
        const finalDescInput = document.getElementById('trailer-final-desc');
        const finalTagsInput = document.getElementById('trailer-final-tags');

        let displayTitle = data.trailer_title;
        if (!displayTitle) {
            const rawTitle = data.video_title || '';
            displayTitle = rawTitle.split('|')[0].split('-')[0].trim() || rawTitle.trim();
        }
        if (titleEl) titleEl.innerText = displayTitle || 'Akıllı Fragman';
        if (finalTitleInput) {
            finalTitleInput.value = displayTitle || '';
            finalTitleInput.oninput = () => window.saveTrailerTextChanges();
        }

        const origTitleEl = document.getElementById('trailer-result-orig-title');
        if (origTitleEl) {
            const origTitle = data.original_title || data.youtube_url || '';
            if (origTitle && origTitle !== displayTitle) {
                origTitleEl.innerHTML = `<i class="fa-brands fa-youtube text-red-500 mr-1"></i>${escapeHtml(origTitle)}`;
                origTitleEl.classList.remove('hidden');
            } else {
                origTitleEl.classList.add('hidden');
            }
        }

        if (durationEl) {
            const durVal = data.trailer_duration || data.duration || (data.scenes && data.scenes.length > 0 ? data.scenes.reduce((acc, s) => acc + (s.duration || 0), 0) : 60);
            durationEl.innerText = formatSec(durVal);
        }

        let displayDesc = data.description;
        if (!displayDesc && data.scenes && data.scenes.length > 0) {
            const sums = data.scenes.map(s => s.summary).filter(Boolean);
            if (sums.length > 0) {
                displayDesc = sums.slice(0, 2).join(' ') + ' Projenin tüm kilit anları ve sonuçları bu videoda! 👇';
            }
        }
        if (displayDesc) {
            displayDesc = displayDesc.replace(/(👇\s*[\.\,\:]*\s*)+/g, '👇\n\n').replace(/\n{3,}/g, '\n\n').trim();
        }
        const ytUrl = data.youtube_url || (currentProject && currentProject.youtube_url) || '';
        if (ytUrl && displayDesc && !displayDesc.includes(ytUrl)) {
            displayDesc = `${displayDesc}\n\n🎬 Videonun tamamı: ${ytUrl}`.trim();
        }
        if (finalDescInput) {
            finalDescInput.value = displayDesc || '';
            finalDescInput.oninput = () => window.saveTrailerTextChanges();
        }

        let displayTags = data.hashtags;
        if (!displayTags || !Array.isArray(displayTags) || displayTags.length === 0 || displayTags.includes('#ClipForge')) {
            displayTags = ['#yapayzeka', '#teknoloji', '#proje', '#reels', '#kesfet'];
        }
        if (finalTagsInput) {
            finalTagsInput.value = displayTags.join(' ');
            finalTagsInput.oninput = () => window.saveTrailerTextChanges();
        }

        if (videoPlayer && data.video_url) {
            const cleanUrl = data.video_url.split('?')[0];
            const freshUrl = `${cleanUrl}?v=${Date.now()}`;
            videoPlayer.preload = 'metadata';
            videoPlayer.src = freshUrl;
            videoPlayer.load();
        }

        // Sahne Listesi Dökümü
        if (scenesListEl && data.scenes && data.scenes.length > 0) {
            scenesListEl.innerHTML = data.scenes.map((sc, idx) => `
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2 hover:border-purple-500/40 transition-all">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-5 h-5 rounded-full bg-purple-600 text-white text-[11px] font-bold flex items-center justify-center shadow-sm">
                                ${sc.act_number || (idx + 1)}
                            </span>
                            <h5 class="text-xs font-bold text-white">${escapeHtml(sc.chapter_title || 'Bölüm')}</h5>
                        </div>
                        <span class="text-[11px] font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded">
                            ${formatSec(sc.start_time)} - ${formatSec(sc.end_time)} (${sc.duration}s)
                        </span>
                    </div>
                    ${sc.summary ? `<p class="text-[11px] text-slate-300 font-medium">${escapeHtml(sc.summary)}</p>` : ''}
                    ${sc.quote ? `<p class="text-[11px] text-slate-400 italic border-l-2 border-purple-500/40 pl-2.5">"${escapeHtml(sc.quote)}"</p>` : ''}
                </div>
            `).join('');
        }

        // 1. İndir butonu: Direkt native link olarak ayarla (iOS & Android tarayıcıları engellemez)
        if (downloadBtn && data.video_url) {
            downloadBtn.href = data.video_url;
            downloadBtn.setAttribute('download', data.video_filename || 'trailer.mp4');
            const sizeBadge = data.file_size_mb ? ` (${data.file_size_mb} MB)` : '';
            downloadBtn.innerHTML = `<i class="fa-solid fa-download text-indigo-400 text-xs"></i> <span>Fragmanı İndir${sizeBadge}</span>`;
            downloadBtn.onclick = () => {
                showToast('🎬 Fragman indiriliyor... Galerinize kaydedilmektedir.', 'info');
            };
        }

        // 2. Doğrudan Paylaş Butonu: Video dosyasını telefonda doğrudan Reels / TikTok'a gönder (Web Share API)
        if (shareBtn && data.video_url) {
            shareBtn.innerHTML = '<i class="fa-solid fa-paper-plane text-sm"></i> <span>Telefonda Doğrudan Paylaş (Reels / TikTok / Shorts)</span>';
            shareBtn.disabled = false;
            shareBtn.className = 'w-full bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white text-sm font-bold py-3 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-purple-600/25 active:scale-[0.98] transition-all min-h-[46px] cursor-pointer';

            const trailerId = data.trailer_id || 'active';
            const filename = data.video_filename || `trailer_${trailerId}.mp4`;

            // Arka planda fragman dosyasını önceden hafızaya al (0ms Instant Share için)
            if (data.trailer_id) {
                window.preloadTrailerFile(data.trailer_id, data.video_url, filename);
            }

            shareBtn.onclick = async () => {
                await window.saveTrailerTextChanges();
                const captionInfo = window.getLatestTrailerCaption();

                // 1. Açıklamayı her halükarda panoya kopyala
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(captionInfo.fullCaption);
                    }
                } catch (e) {}

                // 2. Video zaten önceden indirilip hafızaya alınmış mı? (0ms Instant Share - User Gesture Taze!)
                let cachedFile = window.trailerFilesCache && window.trailerFilesCache[trailerId];
                if (cachedFile) {
                    if (navigator.canShare && navigator.canShare({ files: [cachedFile] })) {
                        try {
                            await navigator.share({
                                files: [cachedFile],
                                title: captionInfo.title,
                                text: captionInfo.fullCaption
                            });
                            showToast('🎉 Video paylaşım menüsü açıldı! Başlık panoya kopyalandı.', 'success');
                            return;
                        } catch (err) {
                            if (err.name === 'AbortError') return;
                            console.warn('Trailer share error with cached file:', err);
                            showToast('Paylaşım menüsü açılamadı: ' + err.message, 'error');
                            return;
                        }
                    } else if (navigator.share) {
                        try {
                            await navigator.share({
                                title: captionInfo.title,
                                text: captionInfo.fullCaption,
                                url: window.location.origin + data.video_url
                            });
                            showToast('🎉 Paylaşım menüsü açıldı! Başlık panoya kopyalandı.', 'success');
                        } catch (e) {}
                        return;
                    }
                }

                // 3. Hafızada henüz yoksa: Butonu 'Video Hazırlanıyor' yap, indir ve 'Şimdi Aç' moduna geçir
                const originalHtml = shareBtn.innerHTML;
                const originalClass = shareBtn.className;
                shareBtn.disabled = true;
                shareBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i> <span>Video Hazırlanıyor...</span>';
                showToast('📋 Açıklama kopyalandı! Video telefona hazırlanıyor...', 'info');

                try {
                    const response = await fetch(data.video_url);
                    if (!response.ok) throw new Error('Video dosyası indirilemedi.');
                    const blob = await response.blob();
                    const file = new File([blob], filename, { type: 'video/mp4' });
                    window.trailerFilesCache[trailerId] = file;

                    // Gesture süresinin dolmasına karşı: Butonu yeşil yap ve 'Şimdi Dokunun' de
                    shareBtn.disabled = false;
                    shareBtn.className = 'w-full bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 text-white font-semibold py-3 px-4 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/30 active:scale-95 transition-all min-h-[46px] animate-pulse cursor-pointer';
                    shareBtn.innerHTML = '<i class="fa-solid fa-paper-plane text-sm"></i> <span>✅ Hazır! Videoyu Göndermek İçin Dokunun</span>';
                    showToast('✅ Video hazır! Reels / TikTok\'a göndermek için tekrar dokunun.', 'success');
                } catch (err) {
                    shareBtn.disabled = false;
                    shareBtn.innerHTML = originalHtml;
                    shareBtn.className = originalClass;
                    showToast('Video hazırlanamadı: ' + err.message, 'error');
                }
            };
        }

        resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    window.getLatestTrailerCaption = function() {
        const titleEl = document.getElementById('trailer-final-title');
        const descEl = document.getElementById('trailer-final-desc');
        const tagsEl = document.getElementById('trailer-final-tags');

        const title = (titleEl ? titleEl.value : '').trim();
        let desc = (descEl ? descEl.value : '').trim();
        const rawTags = (tagsEl ? tagsEl.value : '').trim();
        const tagsList = rawTags ? rawTags.split(/\s+/).filter(Boolean) : [];

        // Orijinal YouTube linki yoksa açıklamanın altına ekle (Reels ile birebir tutarlı)
        const ytUrl = (activeTrailerData && activeTrailerData.youtube_url) || (currentProject && currentProject.youtube_url) || '';
        if (ytUrl && desc && !desc.includes(ytUrl)) {
            desc = `${desc}\n\n🎬 Videonun tamamı: ${ytUrl}`.trim();
            if (descEl) descEl.value = desc;
        }

        let fullCaption = title;
        if (desc) fullCaption += `\n\n${desc}`;
        if (tagsList.length > 0) fullCaption += `\n\n${tagsList.join(' ')}`;

        return {
            title,
            description: desc,
            hashtags: tagsList,
            fullCaption
        };
    };

    window.saveTrailerTextChanges = async function() {
        const activeTrailerId = localStorage.getItem('clipforge_active_trailer_id');
        if (!activeTrailerId) return;
        const captionInfo = window.getLatestTrailerCaption();
        try {
            await fetchWithAuth(`/api/trailers/${activeTrailerId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: captionInfo.title,
                    description: captionInfo.description,
                    hashtags: captionInfo.hashtags
                })
            });
        } catch (e) {
            console.error('Save trailer text error:', e);
        }
    };

    window.copyEditedTrailerCaption = function(btn) {
        const captionInfo = window.getLatestTrailerCaption();
        navigator.clipboard.writeText(captionInfo.fullCaption).then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400 text-xs"></i> <span>Metin Kopyalandı!</span>';
            showToast('Fragman başlığı, açıklaması ve etiketleri kopyalandı!', 'success');
            setTimeout(() => { btn.innerHTML = orig; }, 2000);
        });
    };

    window.checkAndOpenProjectTrailer = async function(projectId) {
        if (!projectId) return;
        try {
            const res = await fetchWithAuth(`/api/projects/${projectId}/trailer`);
            if (res.ok) {
                const data = await res.json();
                if (data.exists && data.trailer) {
                    window.openTrailerById(data.trailer.trailer_id);
                    return;
                }
            }
            showToast('Bu projeye ait hazır fragman bulunamadı.', 'info');
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    };

    // İlk Yükleme
    checkAuth();

    // Arka planda fragman sayısını çekip rozeti güncelle
    fetchWithAuth('/api/trailers')
        .then(r => r.ok ? r.json() : [])
        .then(list => {
            const b = document.getElementById('history-tab-trailers-badge');
            if (b) b.textContent = list.length;
        })
        .catch(() => {});
});
