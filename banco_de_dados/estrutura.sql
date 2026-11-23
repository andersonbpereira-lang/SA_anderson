PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS pacientes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL,
 data_nascimento TEXT NOT NULL, sexo TEXT NOT NULL CHECK (sexo IN ('M','F')),
 peso_kg REAL NOT NULL CHECK (peso_kg > 0), altura_m REAL NOT NULL CHECK (altura_m > 0),
 imc REAL NOT NULL, tipo_sanguineo TEXT NOT NULL,
 alergias TEXT NOT NULL DEFAULT 'nenhuma', telefone TEXT, criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS atendimentos (
 id INTEGER PRIMARY KEY AUTOINCREMENT, paciente_id INTEGER NOT NULL,
 queixa TEXT NOT NULL, tipo_ferimento TEXT NOT NULL,
 nivel_dor INTEGER NOT NULL CHECK (nivel_dor BETWEEN 0 AND 10),
 saturacao INTEGER NOT NULL CHECK (saturacao BETWEEN 0 AND 100),
 freq_cardiaca INTEGER NOT NULL CHECK (freq_cardiaca > 0),
 temperatura REAL NOT NULL, pressao_sistolica INTEGER NOT NULL,
 pressao_diastolica INTEGER NOT NULL,
 consciente INTEGER NOT NULL CHECK (consciente IN (0,1)),
 pontos INTEGER NOT NULL, nivel_gravidade TEXT NOT NULL, cor TEXT NOT NULL,
 prioridade INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'aguardando',
 data_hora TEXT NOT NULL,
 FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE
);
