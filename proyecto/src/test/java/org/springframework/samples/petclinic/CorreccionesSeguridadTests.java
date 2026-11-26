/*
 * Copyright 2012-2025 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.samples.petclinic;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;

/**
 * APF3 - Re-test automatizado de las correcciones de configuración y manejo de errores:
 * SEC-01 (S02), SEC-03 (S12), SEC-04 (S13), DEF-P01 (S08) y OBS-02 (S07, S09). Usa HTTP
 * real contra un servidor en puerto aleatorio.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class CorreccionesSeguridadTests {

	@LocalServerPort
	private int port;

	private final HttpClient client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build();

	private HttpResponse<String> get(String path) throws Exception {
		return this.client.send(HttpRequest.newBuilder(URI.create("http://localhost:" + this.port + path)).build(),
				HttpResponse.BodyHandlers.ofString());
	}

	@Test
	void s12PaginaPrincipalEnviaCabecerasDefensivas() throws Exception {
		HttpResponse<String> r = get("/");
		assertThat(r.statusCode()).isEqualTo(200);
		assertThat(r.headers().firstValue("X-Content-Type-Options")).hasValue("nosniff");
		assertThat(r.headers().firstValue("X-Frame-Options")).hasValue("DENY");
		assertThat(r.headers().firstValue("Content-Security-Policy")).isPresent();
		assertThat(r.headers().firstValue("Cache-Control")).isPresent();
	}

	@Test
	void s02ActuatorSoloExponeEndpointsNoSensibles() throws Exception {
		assertThat(get("/actuator/health").statusCode()).isEqualTo(200);
		assertThat(get("/actuator/env").statusCode()).isEqualTo(404);
		assertThat(get("/actuator/configprops").statusCode()).isEqualTo(404);
		assertThat(get("/actuator/beans").statusCode()).isEqualTo(404);
	}

	@Test
	void s13RedireccionSinIdentificadorDeSesion() throws Exception {
		HttpRequest post = HttpRequest.newBuilder(URI.create("http://localhost:" + this.port + "/owners/new"))
			.header("Content-Type", "application/x-www-form-urlencoded")
			.POST(HttpRequest.BodyPublishers
				.ofString("firstName=Ana&lastName=SinSesion&address=Av.+Central+123&city=Lima&telephone=9876543210"))
			.build();
		HttpResponse<String> r = this.client.send(post, HttpResponse.BodyHandlers.ofString());
		assertThat(r.statusCode()).isEqualTo(302);
		assertThat(r.headers().firstValue("Location")).isPresent().get().asString().doesNotContain("jsessionid");
	}

	@Test
	void s08MascotaDeOtroPropietarioResponde404() throws Exception {
		// La mascota 2 (Basil) pertenece a la propietaria 2; se pide desde el propietario
		// 1
		HttpResponse<String> r = get("/owners/1/pets/2/edit");
		assertThat(r.statusCode()).isEqualTo(404);
		assertThat(r.body()).doesNotContain("Exception").doesNotContain("at org.springframework");
	}

	@Test
	void s07VisitaParaMascotaAjenaResponde404() throws Exception {
		assertThat(get("/owners/1/pets/2/visits/new").statusCode()).isEqualTo(404);
	}

	@Test
	void s09PropietarioInexistenteResponde404() throws Exception {
		assertThat(get("/owners/999999").statusCode()).isEqualTo(404);
	}

}
