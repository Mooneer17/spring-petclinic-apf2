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

package org.springframework.samples.petclinic.system;

import java.io.IOException;

import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * APF3, SEC-03: adds basic defensive HTTP headers to every response. Static resources
 * keep the cache headers configured by Spring; pages get {@code Cache-Control: no-cache}.
 */
@Component
class SecurityHeadersFilter extends OncePerRequestFilter {

	static final String CONTENT_SECURITY_POLICY = "default-src 'self'; img-src 'self' data:; object-src 'none'; "
			+ "base-uri 'self'; form-action 'self'; frame-ancestors 'none'";

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		response.setHeader("X-Content-Type-Options", "nosniff");
		response.setHeader("X-Frame-Options", "DENY");
		response.setHeader("Content-Security-Policy", CONTENT_SECURITY_POLICY);
		response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
		String path = request.getRequestURI().substring(request.getContextPath().length());
		if (!path.startsWith("/resources/") && !path.startsWith("/webjars/")) {
			response.setHeader("Cache-Control", "no-cache");
		}
		chain.doFilter(request, response);
	}

}
