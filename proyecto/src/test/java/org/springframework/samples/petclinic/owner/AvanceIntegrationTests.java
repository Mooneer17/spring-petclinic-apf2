package org.springframework.samples.petclinic.owner;

import java.time.LocalDate;
import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.data.domain.Pageable;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "spring.docker.compose.enabled=false")
@AutoConfigureMockMvc
@Transactional
class AvanceIntegrationTests {

	@Autowired
	OwnerRepository owners;

	@Autowired
	PetTypeRepository types;

	@Autowired
	EntityManager em;

	@Autowired
	MockMvc mvc;

	private Owner owner() {
		Owner o = new Owner();
		o.setFirstName("Ana");
		o.setLastName("TorresAPF");
		o.setAddress("Av. Central 123");
		o.setCity("Lima");
		o.setTelephone("9876543210");
		owners.saveAndFlush(o);
		return o;
	}

	/**
	 * Prepara una mascota persistida para el propietario indicado.
	 * <p>
	 * Correccion INC-T01 (instrumento de prueba): la version inicial devolvia la
	 * instancia transitoria {@code p}. Como el propietario ya existe,
	 * {@code saveAndFlush} ejecuta {@code merge} y la cascada persiste una copia
	 * gestionada; {@code p} conserva {@code id == null}. Ahora la mascota se recupera
	 * desde la base de datos, de modo que su identificador es el realmente asignado.
	 */
	private Pet pet(Owner o) {
		Pet p = new Pet();
		p.setName("LunaAPF");
		p.setBirthDate(LocalDate.of(2022, 5, 10));
		p.setType(types.findPetTypes().iterator().next());
		o.addPet(p);
		owners.saveAndFlush(o);
		em.clear();
		Pet persisted = owners.findById(o.getId()).orElseThrow().getPet("LunaAPF", true);
		assertThat(persisted).as("fixture: mascota persistida").isNotNull();
		assertThat(persisted.getId()).as("fixture: id asignado por la base de datos").isNotNull();
		return persisted;
	}

	@Test
	void CP02_findOwnerByLastName() {
		Owner o = owner();
		Integer id = o.getId();
		em.clear();
		var matches = owners.findByLastNameStartingWith("TorresAPF", Pageable.unpaged()).getContent();
		assertThat(matches).hasSize(1);
		assertThat(matches.get(0).getId()).isEqualTo(id);
		assertThat(matches.get(0).getFirstName()).isEqualTo("Ana");
		assertThat(matches.get(0).getTelephone()).isEqualTo("9876543210");
	}

	@Test
	void CP03_updatePhoneAndReload() {
		Owner o = owner();
		Integer id = o.getId();
		o.setTelephone("9123456780");
		owners.saveAndFlush(o);
		em.clear();
		Owner read = owners.findById(id).orElseThrow();
		assertThat(read.getId()).isEqualTo(id);
		assertThat(read.getTelephone()).isEqualTo("9123456780");
	}

	@Test
	void CP04_savePetWithCorrectOwner() {
		Owner o = owner();
		Pet p = pet(o);
		Integer id = o.getId();
		Integer petId = p.getId();
		em.clear();
		Pet read = owners.findById(id).orElseThrow().getPet(petId);
		assertThat(read).isNotNull();
		assertThat(read.getName()).isEqualTo("LunaAPF");
		assertThat(read.getBirthDate()).isEqualTo(LocalDate.of(2022, 5, 10));
		assertThat(read.getType()).isNotNull();
	}

	@Test
	void CP06_registerVisitViaWebAndReload() throws Exception {
		Owner o = owner();
		Pet p = pet(o);
		Integer id = o.getId();
		Integer petId = p.getId();
		mvc.perform(post("/owners/{ownerId}/pets/{petId}/visits/new", id, petId)
			.param("date", LocalDate.now().plusDays(1).toString())
			.param("description", "Control general APF")).andExpect(status().is3xxRedirection());
		em.flush();
		em.clear();
		var visits = owners.findById(id).orElseThrow().getPet(petId).getVisits();
		assertThat(visits).hasSize(1);
		Visit v = visits.iterator().next();
		assertThat(v.getDescription()).isEqualTo("Control general APF");
		assertThat(v.getDate()).isEqualTo(LocalDate.now().plusDays(1));
	}

}
