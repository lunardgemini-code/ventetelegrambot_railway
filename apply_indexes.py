import asyncio
import os
from dotenv import load_dotenv

# Charger les variables d'environnement (y compris TURSO_URL et TURSO_TOKEN)
load_dotenv()

from database.db import init_db, get_db

async def main():
    print("Application des index pour optimiser les row reads...")
    await init_db()
    print("Index appliqués avec succès !")
    
if __name__ == "__main__":
    asyncio.run(main())
