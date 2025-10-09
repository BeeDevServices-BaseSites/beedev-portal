(function () {
    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    ready(function () {
        const rows   = Array.from(document.querySelectorAll('#catalog-rows .catalog-row'));
        const grand  = document.getElementById('draft-grand-total');

        if (!grand) {
        console.warn('Missing #draft-grand-total element');
        return;
        }

    function parseNum(v){ const x = parseFloat(v); return isNaN(x) ? 0 : x; }
    function fmtUSD(v){ return '$' + (Math.round(v*100)/100).toFixed(2); }

    function recalcRow(row){
        const hourly  = parseNum(row.dataset.hourly);
        const base    = parseNum(row.dataset.base);
        const checked = row.querySelector('.js-select')?.checked;
        const hours   = parseNum(row.querySelector('.js-hours')?.value);
        const qty     = parseNum(row.querySelector('.js-qty')?.value);
        const cell    = row.querySelector('.line-total');

        if (!cell) return 0;
        if (!checked) { cell.textContent = '—'; return 0; }

        const total = (hours * qty * hourly) + base;
        cell.textContent = fmtUSD(total);
        return total;
    }

    function recalcAll(){
        let sum = 0;
        rows.forEach(row => { sum += recalcRow(row); });
        grand.textContent = fmtUSD(sum);
    }

    function onRowChange(e){
        const t = e.target;
        if (!t) return;
        if (t.classList.contains('js-select') ||
            t.classList.contains('js-hours')  ||
            t.classList.contains('js-qty')) {
            recalcAll();
        }
    }

    rows.forEach(row => {
        row.addEventListener('input', onRowChange);
        row.addEventListener('change', onRowChange);
    });

        recalcAll();
    });
})();
