// Auto-dismiss flash messages
document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(100%)';
        el.style.transition = 'all 0.3s';
        setTimeout(() => el.remove(), 300);
    }, 4000);
});

// Toggle password visibility
function togglePwd(id, btn) {
    const input = document.getElementById(id);
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁';
    }
}

// Toast notification
function showToast(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// Format number input as currency
document.querySelectorAll('input[type="number"][name="amount"]').forEach(inp => {
    inp.addEventListener('blur', () => {
        if (inp.value) inp.value = parseFloat(inp.value).toFixed(2);
    });
});

// Phone number formatting
document.querySelectorAll('input[type="tel"]').forEach(inp => {
    inp.addEventListener('input', (e) => {
        let val = e.target.value.replace(/\D/g, '');
        if (val.startsWith('8')) val = '7' + val.slice(1);
        if (val.startsWith('7') && val.length > 1) {
            let formatted = '+7';
            if (val.length > 1) formatted += ' (' + val.slice(1, 4);
            if (val.length > 4) formatted += ') ' + val.slice(4, 7);
            if (val.length > 7) formatted += '-' + val.slice(7, 9);
            if (val.length > 9) formatted += '-' + val.slice(9, 11);
            e.target.value = formatted;
        }
    });
});

// Account number formatting (auto-spacing display)
const accountInput = document.getElementById('toAccount');
if (accountInput) {
    accountInput.addEventListener('input', () => {
        accountInput.value = accountInput.value.replace(/[^0-9]/g, '').slice(0, 20);
    });
}
