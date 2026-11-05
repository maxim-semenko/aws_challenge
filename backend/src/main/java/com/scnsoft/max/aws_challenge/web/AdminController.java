package com.scnsoft.max.aws_challenge.web;

import com.scnsoft.max.aws_challenge.security.CurrentUserResolver;
import com.scnsoft.max.aws_challenge.user.AppUser;
import com.scnsoft.max.aws_challenge.user.AppUserRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

/** Admin Lambda routes: /api/admin/** (Cognito group "admin" required). */
@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final CurrentUserResolver currentUserResolver;
    private final AppUserRepository userRepository;

    public record UserDto(Long id, String email, String username, Instant createdAt) {
        static UserDto of(AppUser u) {
            return new UserDto(u.getId(), u.getEmail(), u.getUsername(), u.getCreatedAt());
        }
    }

    public record PageResponse<T>(List<T> items, int page, int size, long total) {
    }

    /** Paginated SELECT ... LIMIT/OFFSET through RDS Proxy. */
    @GetMapping("/users")
    public PageResponse<UserDto> users(@RequestParam(defaultValue = "0") int page,
                                       @RequestParam(defaultValue = "20") int size,
                                       HttpServletRequest request) {
        currentUserResolver.requireAdmin(request);
        Page<AppUser> result = userRepository.findAll(
                PageRequest.of(Math.max(page, 0), Math.clamp(size, 1, 100), Sort.by(Sort.Direction.DESC, "createdAt")));
        return new PageResponse<>(result.map(UserDto::of).getContent(), result.getNumber(), result.getSize(), result.getTotalElements());
    }
}
