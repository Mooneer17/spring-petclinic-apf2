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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;

/**
 * APF3 - Re-test automatizado de E01 (DEF-P02 y DEF-P03). Envía en el mismo instante
 * cuatro altas de la misma mascota para cada propietario y comprueba que no queden
 * mascotas sin propietario, que cada propietario tenga una sola mascota con ese nombre y
 * que ninguna respuesta sea HTTP 5xx.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class E01ConcurrenciaTests {

	private static final int PROPIETARIOS = 5;

	private static final int ENVIOS_POR_PROPIETARIO = 4;

	private static final String NOMBRE = "Gemela";

	@LocalServerPort
	private int port;

	@Autowired
	private OwnerRepository owners;

	@Autowired
	private JdbcTemplate jdbc;

	@Test
	void altasSimultaneasNoDejanHuerfanasNiErrores500() throws Exception {
		List<Integer> ids = new ArrayList<>();
		for (int i = 0; i < PROPIETARIOS; i++) {
			Owner owner = new Owner();
			owner.setFirstName("E01");
			owner.setLastName("Concurrencia" + i);
			owner.setAddress("Av. Prueba " + i);
			owner.setCity("Lima");
			owner.setTelephone("9876543210");
			ids.add(this.owners.saveAndFlush(owner).getId());
		}
		Integer huerfanasAntes = this.jdbc.queryForObject("SELECT COUNT(*) FROM pets WHERE owner_id IS NULL",
				Integer.class);

		HttpClient client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build();
		Map<Integer, AtomicInteger> estados = new ConcurrentHashMap<>();
		ExecutorService pool = Executors.newFixedThreadPool(PROPIETARIOS * ENVIOS_POR_PROPIETARIO);
		CountDownLatch inicio = new CountDownLatch(1);
		CountDownLatch fin = new CountDownLatch(PROPIETARIOS * ENVIOS_POR_PROPIETARIO);
		for (Integer id : ids) {
			for (int k = 0; k < ENVIOS_POR_PROPIETARIO; k++) {
				pool.submit(() -> {
					try {
						inicio.await();
						HttpRequest req = HttpRequest
							.newBuilder(URI.create("http://localhost:" + this.port + "/owners/" + id + "/pets/new"))
							.header("Content-Type", "application/x-www-form-urlencoded")
							.POST(HttpRequest.BodyPublishers
								.ofString("name=" + NOMBRE + "&birthDate=2020-01-01&type=cat"))
							.build();
						int status = client.send(req, HttpResponse.BodyHandlers.discarding()).statusCode();
						estados.computeIfAbsent(status, s -> new AtomicInteger()).incrementAndGet();
					}
					catch (Exception ex) {
						estados.computeIfAbsent(-1, s -> new AtomicInteger()).incrementAndGet();
					}
					finally {
						fin.countDown();
					}
				});
			}
		}
		inicio.countDown();
		assertThat(fin.await(60, TimeUnit.SECONDS)).isTrue();
		pool.shutdown();

		Integer huerfanasDespues = this.jdbc.queryForObject("SELECT COUNT(*) FROM pets WHERE owner_id IS NULL",
				Integer.class);
		System.out.println("E01 respuestas=" + estados + " huerfanasAntes=" + huerfanasAntes + " huerfanasDespues="
				+ huerfanasDespues);

		assertThat(estados.keySet()).as("ninguna respuesta 5xx ni error de conexión")
			.allMatch(status -> status >= 200 && status < 500);
		assertThat(huerfanasDespues).as("mascotas sin propietario").isEqualTo(huerfanasAntes);
		for (Integer id : ids) {
			Integer conNombre = this.jdbc.queryForObject("SELECT COUNT(*) FROM pets WHERE owner_id = ? AND name = ?",
					Integer.class, id, NOMBRE);
			assertThat(conNombre).as("mascotas '" + NOMBRE + "' del propietario " + id).isEqualTo(1);
		}
	}

}
