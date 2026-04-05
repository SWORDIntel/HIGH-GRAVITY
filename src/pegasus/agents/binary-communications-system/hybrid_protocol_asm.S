/*
 * HYBRID PROTOCOL ASSEMBLY OPTIMIZATIONS
 * Hand-written x86-64 assembly for ultra-critical paths
 * Separate code paths for P-cores (AVX-512) and E-cores (AVX2)
 */

.intel_syntax noprefix
.text

/*
 * Ultra-fast message copy for P-cores using AVX-512
 * rdi = destination
 * rsi = source  
 * rdx = size (must be multiple of 64)
 */
.global memcpy_avx512_asm
.type memcpy_avx512_asm, @function
.align 64
memcpy_avx512_asm:
    # Save registers
    push rbx
    push r12
    push r13
    
    # Calculate number of 512-bit chunks
    mov rcx, rdx
    shr rcx, 6          # Divide by 64
    jz .Lsmall_copy_512
    
    # Align destination to cache line
    mov rax, rdi
    and rax, 63
    jz .Laligned_512
    
    # Handle unaligned start
    mov r12, 64
    sub r12, rax
    sub rdx, r12
    rep movsb
    mov rcx, rdx
    shr rcx, 6
    
.Laligned_512:
    # Main AVX-512 copy loop - unrolled 4x
    mov rax, rcx
    shr rax, 2          # Divide by 4 for unrolling
    jz .Lremainder_512
    
.Lloop_512:
    # Prefetch next cache lines
    prefetchnta [rsi + 512]
    prefetchnta [rsi + 576]
    
    # Load 4x 512-bit vectors
    vmovdqa64 zmm0, [rsi]
    vmovdqa64 zmm1, [rsi + 64]
    vmovdqa64 zmm2, [rsi + 128]
    vmovdqa64 zmm3, [rsi + 192]
    
    # Non-temporal stores to bypass cache
    vmovntdq [rdi], zmm0
    vmovntdq [rdi + 64], zmm1
    vmovntdq [rdi + 128], zmm2
    vmovntdq [rdi + 192], zmm3
    
    add rsi, 256
    add rdi, 256
    dec rax
    jnz .Lloop_512
    
.Lremainder_512:
    # Handle remaining 64-byte chunks
    and rcx, 3
    jz .Lsmall_copy_512
    
.Lremainder_loop_512:
    vmovdqa64 zmm0, [rsi]
    vmovntdq [rdi], zmm0
    add rsi, 64
    add rdi, 64
    dec rcx
    jnz .Lremainder_loop_512
    
.Lsmall_copy_512:
    # Handle remaining bytes (< 64)
    and rdx, 63
    jz .Ldone_512
    mov rcx, rdx
    rep movsb
    
.Ldone_512:
    sfence              # Ensure stores are visible
    
    # Restore registers
    pop r13
    pop r12
    pop rbx
    ret

/*
 * Ultra-fast message copy for E-cores using AVX2
 * rdi = destination
 * rsi = source
 * rdx = size (must be multiple of 32)
 */
.global memcpy_avx2_asm
.type memcpy_avx2_asm, @function
.align 64
memcpy_avx2_asm:
    # Save registers
    push rbx
    push r12
    
    # Calculate number of 256-bit chunks
    mov rcx, rdx
    shr rcx, 5          # Divide by 32
    jz .Lsmall_copy_avx2
    
    # E-cores benefit from different unrolling
    mov rax, rcx
    shr rax, 3          # Divide by 8 for unrolling
    jz .Lremainder_avx2
    
.Lloop_avx2:
    # E-cores have smaller caches, prefetch less aggressively
    prefetcht0 [rsi + 256]
    
    # Load 8x 256-bit vectors
    vmovdqa ymm0, [rsi]
    vmovdqa ymm1, [rsi + 32]
    vmovdqa ymm2, [rsi + 64]
    vmovdqa ymm3, [rsi + 96]
    vmovdqa ymm4, [rsi + 128]
    vmovdqa ymm5, [rsi + 160]
    vmovdqa ymm6, [rsi + 192]
    vmovdqa ymm7, [rsi + 224]
    
    # Stream stores for E-cores
    vmovntdq [rdi], ymm0
    vmovntdq [rdi + 32], ymm1
    vmovntdq [rdi + 64], ymm2
    vmovntdq [rdi + 96], ymm3
    vmovntdq [rdi + 128], ymm4
    vmovntdq [rdi + 160], ymm5
    vmovntdq [rdi + 192], ymm6
    vmovntdq [rdi + 224], ymm7
    
    add rsi, 256
    add rdi, 256
    dec rax
    jnz .Lloop_avx2
    
.Lremainder_avx2:
    # Handle remaining 32-byte chunks
    and rcx, 7
    jz .Lsmall_copy_avx2
    
.Lremainder_loop_avx2:
    vmovdqa ymm0, [rsi]
    vmovntdq [rdi], ymm0
    add rsi, 32
    add rdi, 32
    dec rcx
    jnz .Lremainder_loop_avx2
    
.Lsmall_copy_avx2:
    # Handle remaining bytes (< 32)
    and rdx, 31
    jz .Ldone_avx2
    mov rcx, rdx
    rep movsb
    
.Ldone_avx2:
    sfence
    
    # Restore registers
    pop r12
    pop rbx
    ret

/*
 * Hardware CRC32C using PCLMULQDQ (works on both P and E cores)
 * rdi = data pointer
 * rsi = length
 * Returns CRC32C in rax
 */
.global crc32c_hw_asm
.type crc32c_hw_asm, @function
.align 16
crc32c_hw_asm:
    mov rax, 0xFFFFFFFF    # Initial CRC value
    
    # Process 8 bytes at a time
    mov rcx, rsi
    shr rcx, 3
    jz .Lcrc_small
    
.Lcrc_loop:
    crc32 rax, qword ptr [rdi]
    add rdi, 8
    dec rcx
    jnz .Lcrc_loop
    
.Lcrc_small:
    # Handle remaining bytes
    and rsi, 7
    jz .Lcrc_done
    
.Lcrc_byte_loop:
    crc32 rax, byte ptr [rdi]
    inc rdi
    dec rsi
    jnz .Lcrc_byte_loop
    
.Lcrc_done:
    not rax                # Final XOR
    ret

/*
 * Atomic ring buffer write with TSX (for P-cores only)
 * rdi = ring buffer pointer
 * rsi = data pointer
 * rdx = data size
 * Returns 1 on success, 0 on failure
 */
.global ring_write_tsx
.type ring_write_tsx, @function
.align 16
ring_write_tsx:
    push rbx
    push r12
    push r13
    
    mov r12, rdi           # Save ring buffer pointer
    mov r13, rsi           # Save data pointer
    mov rbx, rdx           # Save data size
    
    # Try hardware transactional memory
    xbegin .Ltsx_abort
    
    # Inside transaction - do atomic write
    mov rax, [r12]         # Load write position
    mov rcx, [r12 + 8]     # Load read position
    
    # Check space
    lea rdx, [rax + rbx]
    cmp rdx, rcx
    ja .Ltsx_abort
    
    # Calculate buffer offset
    mov rdx, [r12 + 16]    # Load buffer base
    and rax, [r12 + 24]    # Apply mask
    add rdx, rax
    
    # Copy data (small copy inside transaction)
    mov rcx, rbx
    mov rdi, rdx
    mov rsi, r13
    rep movsb
    
    # Update write position
    add qword ptr [r12], rbx
    
    xend                   # Commit transaction
    mov rax, 1            # Success
    jmp .Lring_done
    
.Ltsx_abort:
    # Fall back to lock-based approach
    xor rax, rax          # Failure
    
.Lring_done:
    pop r13
    pop r12
    pop rbx
    ret

/*
 * SIMD compare for message routing (AVX-512 for P-cores)
 * rdi = message array
 * rsi = target agent ID (broadcast to all lanes)
 * rdx = count
 * Returns bitmap in rax of matching messages
 */
.global find_messages_avx512
.type find_messages_avx512, @function
.align 16
find_messages_avx512:
    vpbroadcastw zmm0, esi  # Broadcast target ID to all lanes
    xor rax, rax            # Clear result bitmap
    xor rcx, rcx            # Counter
    
.Lfind_loop_512:
    cmp rcx, rdx
    jae .Lfind_done_512
    
    # Load 32 message target IDs (16-bit each)
    vmovdqu16 zmm1, [rdi + rcx * 2]
    
    # Compare with target
    vpcmpeqw k1, zmm0, zmm1
    
    # Store mask result
    kmovq rbx, k1
    or rax, rbx
    
    add rcx, 32
    jmp .Lfind_loop_512
    
.Lfind_done_512:
    ret

/*
 * SIMD compare for message routing (AVX2 for E-cores)
 * rdi = message array
 * rsi = target agent ID
 * rdx = count
 * Returns bitmap in rax of matching messages
 */
.global find_messages_avx2
.type find_messages_avx2, @function
.align 16
find_messages_avx2:
    vpbroadcastw ymm0, esi  # Broadcast target ID
    xor rax, rax
    xor rcx, rcx
    
.Lfind_loop_avx2:
    cmp rcx, rdx
    jae .Lfind_done_avx2
    
    # Load 16 message target IDs
    vmovdqu ymm1, [rdi + rcx * 2]
    
    # Compare
    vpcmpeqw ymm2, ymm0, ymm1
    
    # Extract mask
    vpmovmskb ebx, ymm2
    or eax, ebx
    
    add rcx, 16
    jmp .Lfind_loop_avx2
    
.Lfind_done_avx2:
    ret

/*
 * Optimized spinlock using PAUSE instruction
 * rdi = lock pointer
 */
.global spin_lock_optimized
.type spin_lock_optimized, @function
.align 16
spin_lock_optimized:
    mov eax, 1
    
.Lspin_retry:
    xchg [rdi], eax       # Atomic exchange
    test eax, eax
    jz .Lspin_acquired
    
.Lspin_wait:
    pause                 # CPU hint for spinlock
    mov eax, [rdi]        # Check lock state
    test eax, eax
    jnz .Lspin_wait
    
    mov eax, 1
    jmp .Lspin_retry
    
.Lspin_acquired:
    ret

/*
 * Unlock
 * rdi = lock pointer
 */
.global spin_unlock
.type spin_unlock, @function
.align 16
spin_unlock:
    mov dword ptr [rdi], 0
    ret

/* Performance monitoring using RDPMC */
.global read_perf_counter
.type read_perf_counter, @function
.align 16
read_perf_counter:
    mov ecx, edi          # Counter index
    rdpmc
    shl rdx, 32
    or rax, rdx
    ret

/* Read TSC for timing */
.global read_tsc
.type read_tsc, @function
.align 16
read_tsc:
    rdtscp
    shl rdx, 32
    or rax, rdx
    ret

/* Cache line flush */
.global flush_cache_line
.type flush_cache_line, @function
.align 16
flush_cache_line:
    clflush [rdi]
    ret

/* Prefetch for write */
.global prefetch_write
.type prefetch_write, @function
.align 16
prefetch_write:
    prefetchw [rdi]
    ret

.section .note.GNU-stack,"",@progbits