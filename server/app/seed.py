from app.persistence.seed import reset_and_seed


if __name__ == "__main__":
    print("Resetting and seeding database...")
    reset_and_seed()
    print("Done. Database seeded successfully.")
