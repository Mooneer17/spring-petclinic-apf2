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
package org.springframework.samples.petclinic.owner;

import java.util.Optional;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

import jakarta.persistence.LockModeType;

/**
 * Repository class for <code>Owner</code> domain objects. All method names are compliant
 * with Spring Data naming conventions so this interface can easily be extended for Spring
 * Data. See:
 * https://docs.spring.io/spring-data/jpa/docs/current/reference/html/#repositories.query-methods.query-creation
 *
 * @author Ken Krebs
 * @author Juergen Hoeller
 * @author Sam Brannen
 * @author Michael Isvy
 * @author Wick Dynex
 */
public interface OwnerRepository extends JpaRepository<Owner, Integer> {

	/**
	 * Retrieve {@link Owner}s from the data store by last name, returning all owners
	 * whose last name <i>starts</i> with the given name.
	 * @param lastName Value to search for
	 * @return a Collection of matching {@link Owner}s (or an empty Collection if none
	 * found)
	 */
	Page<Owner> findByLastNameStartingWith(String lastName, Pageable pageable);

	/**
	 * Retrieve an {@link Owner} from the data store by id.
	 * <p>
	 * This method returns an {@link Optional} containing the {@link Owner} if found. If
	 * no {@link Owner} is found with the provided id, it will return an empty
	 * {@link Optional}.
	 * </p>
	 * @param id the id to search for
	 * @return an {@link Optional} containing the {@link Owner} if found, or an empty
	 * {@link Optional} if not found.
	 * @throws IllegalArgumentException if the id is null (assuming null is not a valid
	 * input for id)
	 */
	Optional<Owner> findById(Integer id);

	/**
	 * Retrieve an {@link Owner} locking its row until the current transaction ends
	 * (SELECT ... FOR UPDATE), so that concurrent requests for the same owner are
	 * serialized.
	 * @param id the id to search for
	 * @return the locked owner, if found
	 */
	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("SELECT owner FROM Owner owner WHERE owner.id = :id")
	Optional<Owner> findByIdForUpdate(@Param("id") Integer id);

	/**
	 * Add a new pet to the owner inside one transaction, re-reading the owner with a
	 * pessimistic lock. Two simultaneous requests can no longer save stale copies of the
	 * owner that unlink each other's pets (DEF-P02), and the second request sees the pet
	 * saved by the first one, so a duplicate name is rejected instead of failing in the
	 * database (DEF-P03).
	 * @param ownerId the owner id
	 * @param pet the new pet
	 * @return {@code true} if the pet was added, {@code false} if the owner already has a
	 * pet with the same name
	 */
	@Transactional
	default boolean addPetIfNameAvailable(Integer ownerId, Pet pet) {
		Owner owner = findByIdForUpdate(ownerId)
			.orElseThrow(() -> new IllegalStateException("Owner not found with id: " + ownerId));
		if (owner.getPet(pet.getName(), true) != null) {
			return false;
		}
		owner.addPet(pet);
		saveAndFlush(owner);
		return true;
	}

}
