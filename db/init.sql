-- ============================================================
--  Script de inicialización de la base de datos "inventario"
--  MySQL lo ejecuta automáticamente SOLO la primera vez,
--  cuando el volumen datos_mysql está vacío.
-- ============================================================

SET NAMES utf8mb4;
USE inventario;

CREATE TABLE IF NOT EXISTS platillos (
    id_pla INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(40) NOT NULL,
    descripcion TINYTEXT,
    tipo ENUM('Entradas','Bebidas','Platillos','Salsas','Postres') NOT NULL,
    precio DECIMAL(5, 2) NOT NULL,
    dispo BOOL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredientes (
        id_ing INT AUTO_INCREMENT PRIMARY KEY,
    	nombre VARCHAR(25) NOT NULL,
   	proporcion VARCHAR(25) NOT NULL,
    	cantidad DECIMAL(12, 3) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS necesita (
	platillo INT NOT NULL,
	ingrediente INT NOT NULL,
	cantidad DECIMAL(6, 3) NOT NULL DEFAULT 1,
	PRIMARY KEY (platillo, ingrediente),
	FOREIGN KEY (platillo) REFERENCES platillos (id_pla),
	FOREIGN KEY (ingrediente) REFERENCES ingredientes (id_ing)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Registros de ejemplo (datos ficticios)
INSERT INTO platillos (titulo, descripcion, tipo, precio, dispo) VALUES
('Tacos de Carne Asada', 'Tres tacos de carne asada en tortilla de maíz.', 'Platillos', 140, TRUE),
('Quesadillas', 'Tres quesadillas de tortilla de maíz.', 'Platillos', 120, TRUE),
('Horchata', 'Un vaso de medio litro de horchata.', 'Bebidas', 60, TRUE);

INSERT INTO ingredientes (nombre, proporcion, cantidad) VALUES
('Tortilla de maiz', '1 Tortilla', 100),
('Carne de res', '1 Kilogramo', 40),
('Queso', '1 Kilogramo', 30),
('Horchata', '1 Litro', 20);

INSERT INTO necesita (platillo, ingrediente, cantidad) VALUES
(1, 1, 1),
(1, 2, 0.12),
(2, 1, 2),
(2, 3, 0.09),
(3, 4, 0.5);
