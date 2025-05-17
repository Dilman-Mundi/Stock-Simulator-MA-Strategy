const range = document.getElementById("range");
const input = document.getElementById("money");

range.oninput = () => {
    input.value = range.value*1000;
    input.dispatchEvent(new Event('input'));
}

input.addEventListener('input', function(e) {
    let value = e.target.value.replace(/[^\d]/g, '');
    if (isNaN(value)) return;
    e.target.value = "$" + Number(value).toLocaleString('en-US');
});