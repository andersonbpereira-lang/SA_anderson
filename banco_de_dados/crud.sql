-- Consultar pacientes
SELECT id, nome, data_nascimento, sexo FROM pacientes ORDER BY nome;
-- Histórico do paciente (substitua ? por parâmetro no código)
SELECT * FROM atendimentos WHERE paciente_id = ? ORDER BY data_hora DESC;
-- Fila didática de espera
SELECT a.id, p.nome, a.cor, a.nivel_gravidade, a.data_hora
FROM atendimentos a JOIN pacientes p ON p.id = a.paciente_id
WHERE a.status = 'aguardando' ORDER BY a.prioridade, a.data_hora, a.id;
-- Atualizar situação
UPDATE atendimentos SET status = ? WHERE id = ?;
-- Excluir paciente; a FK remove seus atendimentos em cascata
DELETE FROM pacientes WHERE id = ?;
