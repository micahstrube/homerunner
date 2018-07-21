from homerunner import app
import homerunner.db_utils

if __name__ == "__main__":
    with app.app_context():
        # Initialize the database. This creates tables if they
        # don't already exist
        homerunner.db_utils.init_db()
        # Start the application
        app.run(ssl_context='adhoc')
