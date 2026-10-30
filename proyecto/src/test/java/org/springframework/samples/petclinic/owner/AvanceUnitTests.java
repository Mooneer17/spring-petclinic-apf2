package org.springframework.samples.petclinic.owner;

import java.time.LocalDate;
import jakarta.validation.Validation;
import org.junit.jupiter.api.Test;
import org.springframework.validation.BeanPropertyBindingResult;
import static org.assertj.core.api.Assertions.assertThat;

class AvanceUnitTests {

	@Test
	void CP01_telephoneNineDigitsRejectedTenAccepted() {
		try (var factory = Validation.buildDefaultValidatorFactory()) {
			var validator = factory.getValidator();
			Owner owner = new Owner();
			owner.setFirstName("Ana");
			owner.setLastName("Torres");
			owner.setAddress("Av. Central 123");
			owner.setCity("Lima");
			owner.setTelephone("987654321");
			assertThat(validator.validateProperty(owner, "telephone")).isNotEmpty();
			owner.setTelephone("9876543210");
			assertThat(validator.validate(owner)).isEmpty();
		}
	}

	@Test
	void CP05_emptyPetNameRejectedValidNameAccepted() {
		Pet pet = new Pet();
		pet.setBirthDate(LocalDate.of(2022, 5, 10));
		PetType type = new PetType();
		type.setName("cat");
		pet.setType(type);
		pet.setName("");
		var errors = new BeanPropertyBindingResult(pet, "pet");
		new PetValidator().validate(pet, errors);
		assertThat(errors.hasFieldErrors("name")).isTrue();
		pet.setName("Luna");
		var valid = new BeanPropertyBindingResult(pet, "pet");
		new PetValidator().validate(pet, valid);
		assertThat(valid.hasErrors()).isFalse();
	}

}
