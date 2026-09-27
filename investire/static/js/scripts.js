const myModal = document.getElementById('myModal');

myModal.addEventListener('show.bs.modal', event => {
  const button = event.relatedTarget;
  const idAtivo = button.getAttribute('data-ativo-id');
  const confirmBtn = myModal.querySelector('#delete');
  confirmBtn.href = "/excluir_ativo/" + idAtivo;
});