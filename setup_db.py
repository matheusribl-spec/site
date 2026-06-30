import logging

import models

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

if __name__ == "__main__":
    logging.info("Inicializando banco de dados...")
    models.initialize_database()
    logging.info("Banco de dados pronto.")
