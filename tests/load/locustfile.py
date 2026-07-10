from locust import HttpUser, task, between

class PrislabUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # We assume load testing environment handles auth or bypasses it for load tests,
        # or we could authenticate if we have credentials. For this load test baseline,
        # we focus on hitting public endpoints or endpoints that accept load test headers.
        self.client.get("/")

    @task(3)
    def index(self):
        self.client.get("/")

    @task(1)
    def buscar_paciente(self):
        # Simula busqueda en recepcion
        self.client.get("/laboratorio/api/buscar-paciente/?q=Juan")

    @task(2)
    def catalogo_lims(self):
        # Simula cargar catalogos
        self.client.get("/laboratorio/api/catalogo-estudios/")
