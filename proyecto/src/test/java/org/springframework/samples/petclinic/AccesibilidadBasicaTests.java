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
 * APF3: comprobaciones automaticas de los hallazgos de accesibilidad corregidos (A11Y-01
 * a A11Y-05, WCAG 2.1 A/AA). El contraste (A11Y-02) se verifica con axe-core.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class AccesibilidadBasicaTests {

	@LocalServerPort
	private int port;

	private final HttpClient client = HttpClient.newHttpClient();

	private String get(String path) throws Exception {
		HttpRequest request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + path))
			.header("Accept", "text/html")
			.GET()
			.build();
		return client.send(request, HttpResponse.BodyHandlers.ofString()).body();
	}

	@Test
	void a11y01TodasLasPaginasDeclaranIdioma() throws Exception {
		for (String path : new String[] { "/", "/owners/find", "/owners/1", "/vets.html", "/oups" }) {
			assertThat(get(path)).as(path).containsPattern("<html[^>]*\\slang=\"[a-z]{2}\"");
		}
	}

	@Test
	void a11y03EnlaceDelLogoTieneNombreAccesible() throws Exception {
		assertThat(get("/")).containsPattern("<a class=\"navbar-brand\"[^>]*aria-label=\"[^\"]+\"");
	}

	@Test
	void a11y04ImagenesTienenTextoAlternativo() throws Exception {
		for (String path : new String[] { "/", "/oups" }) {
			assertThat(get(path)).as(path).doesNotContainPattern("<img(?![^>]*\\salt=)[^>]*>");
		}
	}

	@Test
	void a11y05CampoDeBusquedaTieneEtiquetaAsociada() throws Exception {
		String body = get("/owners/find");
		assertThat(body).contains("for=\"lastName\"").contains("id=\"lastName\"");
	}

}
