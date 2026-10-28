'use strict';
const form = document.querySelector('#settings');
form.addEventListener('submit', event => event.preventDefault());
const buttons = [...document.querySelectorAll('[data-action]')];
let token = '';
let running = false;
let connected = false;
function render(status) {
  token = status.token;
  connected = true;
  running = status.state === 'running';
  const names = {idle:'준비됨', running:'진행 중', done:'완료', error:'오류'};
  document.querySelector('#state').textContent = names[status.state] || status.state;
  document.querySelector('#status-title').textContent = running ? '페이지를 정리하고 있어요' : status.state === 'done' ? '작업이 완료되었습니다' : status.state === 'error' ? '설정을 확인해주세요' : '다음 기록을 준비하세요';
  document.querySelector('#logs').textContent = status.messages.length ? status.messages.join('\n') : '아직 시작한 작업이 없습니다.';
  document.querySelector('#download').hidden = !status.download;
  buttons.forEach(button => {button.disabled = running;});
}
async function poll() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('서버 상태를 가져올 수 없습니다.');
    if (!connected) document.querySelector('#error').textContent = '';
    render(await response.json());
  } catch (error) {
    connected = false;
    buttons.forEach(button => {button.disabled = true;});
    document.querySelector('#state').textContent = '연결 끊김';
    document.querySelector('#error').textContent = error.message;
  } finally { window.setTimeout(poll, 1000); }
}
buttons.forEach(button => button.addEventListener('click', async () => {
  if (!connected || running || !form.reportValidity()) return;
  const action = button.dataset.action;
  const data = Object.fromEntries(new FormData(form));
  data.pages = Number(data.pages);
  data.headless = form.elements.headless.checked;
  if (['login', 'capture'].includes(action) && !data.url) {
    document.querySelector('#error').textContent = '리더 URL을 입력해주세요.';
    form.elements.url.focus();
    return;
  }
  document.querySelector('#error').textContent = '';
  buttons.forEach(item => {item.disabled = true;});
  try {
    const response = await fetch(`/api/${action}`, {method:'POST', headers:{'Content-Type':'application/json', 'X-Session-Token':token}, body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '작업을 시작하지 못했습니다.');
    running = true;
  } catch (error) { document.querySelector('#error').textContent = error.message; }
}));
buttons.forEach(button => {button.disabled = true;});
poll();
