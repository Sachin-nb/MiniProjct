// ===================================
// COMPLETE ENHANCED SCRIPT.JS
// ===================================

// Create floating particles
function createParticles() {
    const particleCount = 15;
    const body = document.body;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 20 + 's';
        particle.style.animationDuration = (15 + Math.random() * 10) + 's';
        body.appendChild(particle);
    }
}

// Smooth scroll for internal links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

document.addEventListener('DOMContentLoaded', function () {

    // Create particles
    createParticles();

    // ============================================
    // 🔢 AUTO-CALCULATE OVERALL SCORE
    // ============================================
    const overallScoreInput = document.getElementById('overall_score');
    
    // All score input IDs
    const scoreIds = [
        'ar_score',
        'er_score',
        'fsr_score',
        'cpf_score',
        'ifr_score',
        'isr_score'
    ];

    // Helper function to get value safely
    function getVal(id) {
        const el = document.getElementById(id);
        return el ? parseFloat(el.value) || 0 : 0;
    }

    // Calculate overall score (average of all scores)
    function calculateOverall() {
        if (!overallScoreInput) return;
        
        let total = 0;
        let count = 0;

        scoreIds.forEach(id => {
            const val = getVal(id);
            if (!isNaN(val) && val > 0) {
                total += val;
                count++;
            }
        });

        if (count > 0) {
            const avg = parseFloat((total / count).toFixed(1));
            overallScoreInput.value = avg;
            updateScoreStyle(avg);
        } else {
            overallScoreInput.value = '';
        }
    }

    // Update visual styling based on score - ONLY INPUT FIELD
    function updateScoreStyle(score) {
        const el = overallScoreInput;
        if (!el) return;

        // Remove existing classes
        el.classList.remove("score-low", "score-mid", "score-high", "invalid");

        if (score < 50) {
            el.classList.add("score-low", "invalid");
        } 
        else if (score < 75) {
            el.classList.add("score-mid");
        } 
        else {
            el.classList.add("score-high");
        }

        // Pulse animation
        el.classList.add("score-pulse");
        setTimeout(() => el.classList.remove("score-pulse"), 300);
    }

    // Attach event listeners to all score inputs
    scoreIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            // Calculate on input (real-time)
            input.addEventListener('input', calculateOverall);
            
            // Also calculate on change (for number spinners)
            input.addEventListener('change', calculateOverall);
        }
    });

    // Initial calculation (for edit forms with pre-filled values)
    setTimeout(calculateOverall, 100);

    // ============================================
    // ✅ FORM VALIDATION WITH MODAL
    // ============================================
    const form = document.getElementById('addUniversityForm') || document.getElementById('universityForm');
    
    if (form && overallScoreInput) {
        form.addEventListener('submit', function(event) {
            const score = parseFloat(overallScoreInput.value);
            
            if (isNaN(score) || score < 50) {
                event.preventDefault();
                
                // Show the existing modal
                const modalOverlay = document.getElementById('modalOverlay');
                const modalTitle = document.getElementById('modalTitle');
                const modalMessage = document.getElementById('modalMessage');
                const modalIcon = document.getElementById('modalIcon');
                const modalContent = document.getElementById('modalContent');
                
                if (modalOverlay) {
                    if (modalIcon) modalIcon.textContent = '❌';
                    if (modalTitle) modalTitle.textContent = 'Invalid Score';
                    if (modalMessage) {
                        modalMessage.textContent = 'Cannot add university with overall score below 50. The minimum acceptable score is 50 to ensure quality standards.';
                    }
                    if (modalContent) {
                        modalContent.className = 'modal-content error';
                    }
                    modalOverlay.classList.add('active');
                }
                
                overallScoreInput.classList.add('invalid');
                overallScoreInput.focus();
                
                // Shake animation
                form.style.animation = 'shake 0.5s ease';
                setTimeout(() => form.style.animation = '', 500);
                
                return false;
            }
        });
    }

    // ============================================
    // 🎨 TABLE ROW FADE-IN + RIPPLE CLICK
    // ============================================
    const tableRows = document.querySelectorAll('.rankings-table tbody tr');

    tableRows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(20px)';

        setTimeout(() => {
            row.style.transition = 'all 0.5s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, index * 50);

        row.addEventListener('click', function (e) {
            if (!e.target.classList.contains('view-btn')) {
                const viewBtn = this.querySelector('.view-btn');
                if (viewBtn) createRipple(e, this);
            }
        });
    });

    function createRipple(event, element) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.className = 'ripple-effect';

        element.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    }

    // ============================================
    // 🔍 SEARCH FORM SHAKE + TOAST
    // ============================================
    const searchForms = document.querySelectorAll('.search-form, .search-box form');

    searchForms.forEach(form => {
        const inputs = form.querySelectorAll('input[type="text"]');

        form.addEventListener('submit', function (e) {
            let hasValue = false;

            inputs.forEach(input => {
                if (input.value.trim() !== '') hasValue = true;
            });

            if (!hasValue) {
                e.preventDefault();
                form.style.animation = 'shake 0.5s ease';
                setTimeout(() => form.style.animation = '', 500);

                showToast('Please enter at least one search term', 'warning');
            }
        });
    });

    // ============================================
    // 📱 NAVBAR SCROLL SHRINK
    // ============================================
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            navbar.classList.add('shrink');
        } else {
            navbar.classList.remove('shrink');
        }
    });

});

// ============================================
// 🍞 TOAST NOTIFICATION FUNCTION
// ============================================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 500);
    }, 2500);
}

// ============================================
// 🎯 CUSTOM CURSOR EFFECT
// ============================================



// ============================================
// 💅 ADD DYNAMIC STYLES FOR AUTO-CALC
// ============================================
const style = document.createElement('style');
style.textContent = `
.form-input.score-low {
    background: #ffb3b3 !important;
    color: #7a0000 !important;
    font-weight: 700 !important;
    border: 2px solid #ef4444 !important;
}

.form-input.score-mid {
    background: #ffe7a1 !important;
    color: #7a5d00 !important;
    font-weight: 700 !important;
    border: 2px solid #f59e0b !important;
}

.form-input.score-high {
    background: #c7f7c1 !important;
    color: #115e00 !important;
    font-weight: 700 !important;
    border: 2px solid #10b981 !important;
}

.score-pulse {
    animation: scorePulse 0.3s ease;
}

@keyframes scorePulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

.ripple-effect {
    position: absolute;
    border-radius: 50%;
    background: rgba(102, 126, 234, 0.3);
    transform: scale(0);
    animation: ripple 0.6s ease-out;
    pointer-events: none;
}

@keyframes ripple {
    to {
        transform: scale(2);
        opacity: 0;
    }
}

.toast {
    position: fixed;
    bottom: 30px;
    right: 30px;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    color: white;
    font-weight: 600;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    z-index: 10000;
    animation: slideInUp 0.4s ease;
}

.toast-info {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toast-warning {
    background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
}

.toast-success {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.toast.fade-out {
    animation: fadeOut 0.5s ease;
}

@keyframes slideInUp {
    from {
        transform: translateY(100px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

@keyframes fadeOut {
    to {
        opacity: 0;
        transform: translateY(20px);
    }
}




.particle {
    position: fixed;
    width: 4px;
    height: 4px;
    background: rgba(255, 255, 255, 0.6);
    border-radius: 50%;
    pointer-events: none;
    animation: float linear infinite;
    z-index: 0;
}

@keyframes float {
    from {
        transform: translateY(100vh) rotate(0deg);
        opacity: 0;
    }
    10% {
        opacity: 1;
    }
    90% {
        opacity: 1;
    }
    to {
        transform: translateY(-100px) rotate(360deg);
        opacity: 0;
    }
}
`;
document.head.appendChild(style);