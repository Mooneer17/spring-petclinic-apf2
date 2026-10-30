package org.springframework.samples.petclinic.owner;

import java.time.LocalDate;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Diagnostico de INC-T01. No es un caso del APF; documenta el mecanismo que provoco las
 * fallas iniciales de CP04 y CP06 replicando el helper pet() original.
 */
@SpringBootTest(properties = "spring.docker.compose.enabled=false")
@Transactional
class DiagnosticoFixtureTests {

	@Autowired
	OwnerRepository owners;

	@Autowired
	PetTypeRepository types;

	@Autowired
	EntityManager em;

	@Test
	void DIAG01_originalHelperReturnsTransientPetWithoutId() {
		Owner o = new Owner();
		o.setFirstName("Ana");
		o.setLastName("DiagAPF");
		o.setAddress("Av. Central 123");
		o.setCity("Lima");
		o.setTelephone("9876543210");
		owners.saveAndFlush(o);

		Pet p = new Pet();
		p.setName("LunaDiag");
		p.setBirthDate(LocalDate.of(2022, 5, 10));
		p.setType(types.findPetTypes().iterator().next());
		o.addPet(p);
		Owner returned = owners.saveAndFlush(o);

		// La instancia creada por el test no recibe ID: la cascada MERGE persistio otra.
		assertThat(p.getId()).isNull();
		assertThat(em.contains(p)).isFalse();

		// La mascota si existe en la base de datos con ID asignado.
		em.clear();
		Pet stored = owners.findById(returned.getId()).orElseThrow().getPet("LunaDiag", true);
		assertThat(stored).isNotNull();
		assertThat(stored.getId()).isNotNull();
	}

}
