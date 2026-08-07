class ChessBoard:
    def __init__(self):
        self.board = self._init_board()
        self.turn = 'w'  # 'w' for white, 'b' for black
        self.move_history = []
        self.en_passant_target = None
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.halfmove_clock = 0
        self.fullmove_number = 1

    def _init_board(self):
        board = [[None]*8 for _ in range(8)]
        back_rank = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        for col in range(8):
            board[0][col] = back_rank[col] + 'b'
            board[1][col] = 'p' + 'b'
            board[6][col] = 'p' + 'w'
            board[7][col] = back_rank[col] + 'w'
        return board

    def display(self):
        print("  a b c d e f g h")
        for row in range(8):
            print(8 - row, end=" ")
            for col in range(8):
                piece = self.board[row][col]
                if piece is None:
                    print(".", end=" ")
                else:
                    symbols = {'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚'}
                    s = symbols[piece[0]]
                    if piece[1] == 'w':
                        print(f"\033[97m{s}\033[0m", end=" ")
                    else:
                        print(f"\033[90m{s}\033[0m", end=" ")
            print(8 - row)
        print("  a b c d e f g h")

    def get_piece(self, pos):
        col, row = pos[0], int(pos[1])
        return self.board[8 - row][ord(col) - ord('a')]

    def set_piece(self, pos, piece):
        col, row = pos[0], int(pos[1])
        self.board[8 - row][ord(col) - ord('a')] = piece

    def pos_to_tuple(self, pos):
        return (8 - int(pos[1]), ord(pos[0]) - ord('a'))

    def tuple_to_pos(self, r, c):
        return chr(c + ord('a')) + str(8 - r)

    def is_in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_all_moves(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece[1] == color:
                    moves.extend(self.get_piece_moves(r, c, piece))
        return moves

    def get_piece_moves(self, r, c, piece):
        piece_type = piece[0]
        color = piece[1]
        moves = []

        if piece_type == 'p':
            moves = self._pawn_moves(r, c, color)
        elif piece_type == 'r':
            moves = self._sliding_moves(r, c, color, [(0,1),(0,-1),(1,0),(-1,0)])
        elif piece_type == 'n':
            moves = self._knight_moves(r, c, color)
        elif piece_type == 'b':
            moves = self._sliding_moves(r, c, color, [(1,1),(1,-1),(-1,1),(-1,-1)])
        elif piece_type == 'q':
            moves = self._sliding_moves(r, c, color, [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)])
        elif piece_type == 'k':
            moves = self._king_moves(r, c, color)

        # Filter moves that leave king in check
        legal_moves = []
        for move in moves:
            if not self._move_causes_check(r, c, move[0], move[1], color):
                legal_moves.append(move)
        return legal_moves

    def _pawn_moves(self, r, c, color):
        moves = []
        direction = -1 if color == 'w' else 1
        start_row = 6 if color == 'w' else 1

        # Forward one
        nr, nc = r + direction, c
        if self.is_in_bounds(nr, nc) and self.board[nr][nc] is None:
            moves.append((nr, nc))
            # Forward two
            nr2, nc2 = r + 2*direction, c
            if r == start_row and self.board[nr2][nc2] is None:
                moves.append((nr2, nc2))

        # Captures
        for dc in [-1, 1]:
            nr, nc = r + direction, c + dc
            if self.is_in_bounds(nr, nc):
                if self.board[nr][nc] and self.board[nr][nc][1] != color:
                    moves.append((nr, nc))
                # En passant
                if self.en_passant_target == self.tuple_to_pos(nr, nc):
                    moves.append((nr, nc))

        return moves

    def _sliding_moves(self, r, c, color, directions):
        moves = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.is_in_bounds(nr, nc):
                if self.board[nr][nc] is None:
                    moves.append((nr, nc))
                else:
                    if self.board[nr][nc][1] != color:
                        moves.append((nr, nc))
                    break
                nr += dr
                nc += dc
        return moves

    def _knight_moves(self, r, c, color):
        moves = []
        for dr, dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
            nr, nc = r + dr, c + dc
            if self.is_in_bounds(nr, nc):
                if self.board[nr][nc] is None or self.board[nr][nc][1] != color:
                    moves.append((nr, nc))
        return moves

    def _king_moves(self, r, c, color):
        moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.is_in_bounds(nr, nc):
                    if self.board[nr][nc] is None or self.board[nr][nc][1] != color:
                        moves.append((nr, nc))

        # Castling
        if color == 'w' and r == 7 and c == 4:
            # Kingside
            if self.castling_rights.get('K', False):
                if all(self.board[7][i] is None for i in [5, 6]) and self.board[7][7] == 'r' + 'w':
                    if not self._is_square_attacked(7, 4, 'b') and not self._is_square_attacked(7, 5, 'b') and not self._is_square_attacked(7, 6, 'b'):
                        moves.append((7, 6))
            # Queenside
            if self.castling_rights.get('Q', False):
                if all(self.board[7][i] is None for i in [1, 2, 3]) and self.board[7][0] == 'r' + 'w':
                    if not self._is_square_attacked(7, 4, 'b') and not self._is_square_attacked(7, 3, 'b') and not self._is_square_attacked(7, 2, 'b'):
                        moves.append((7, 2))
        elif color == 'b' and r == 0 and c == 4:
            if self.castling_rights.get('k', False):
                if all(self.board[0][i] is None for i in [5, 6]) and self.board[0][7] == 'r' + 'b':
                    if not self._is_square_attacked(0, 4, 'w') and not self._is_square_attacked(0, 5, 'w') and not self._is_square_attacked(0, 6, 'w'):
                        moves.append((0, 6))
            if self.castling_rights.get('q', False):
                if all(self.board[0][i] is None for i in [1, 2, 3]) and self.board[0][0] == 'r' + 'b':
                    if not self._is_square_attacked(0, 4, 'w') and not self._is_square_attacked(0, 3, 'w') and not self._is_square_attacked(0, 2, 'w'):
                        moves.append((0, 2))
        return moves

    def _is_square_attacked(self, r, c, by_color):
        for rr in range(8):
            for cc in range(8):
                piece = self.board[rr][cc]
                if piece and piece[1] == by_color:
                    attacks = self._get_attacks(rr, cc, piece)
                    if (r, c) in attacks:
                        return True
        return False

    def _get_attacks(self, r, c, piece):
        piece_type = piece[0]
        color = piece[1]
        if piece_type == 'p':
            direction = -1 if color == 'w' else 1
            attacks = []
            for dc in [-1, 1]:
                nr, nc = r + direction, c + dc
                if self.is_in_bounds(nr, nc):
                    attacks.append((nr, nc))
            return attacks
        elif piece_type == 'n':
            attacks = []
            for dr, dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
                nr, nc = r + dr, c + dc
                if self.is_in_bounds(nr, nc):
                    attacks.append((nr, nc))
            return attacks
        elif piece_type in ['r', 'b', 'q']:
            dirs = {'r': [(0,1),(0,-1),(1,0),(-1,0)],
                    'b': [(1,1),(1,-1),(-1,1),(-1,-1)],
                    'q': [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]}
            attacks = []
            for dr, dc in dirs[piece_type]:
                nr, nc = r + dr, c + dc
                while self.is_in_bounds(nr, nc):
                    attacks.append((nr, nc))
                    if self.board[nr][nc] is not None:
                        break
                    nr += dr
                    nc += dc
            return attacks
        elif piece_type == 'k':
            attacks = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if self.is_in_bounds(nr, nc):
                        attacks.append((nr, nc))
            return attacks
        return []

    def _move_causes_check(self, r, c, nr, nc, color):
        # Make a copy and simulate
        piece = self.board[r][c]
        captured = self.board[nr][nc]
        self.board[nr][nc] = piece
        self.board[r][c] = None

        # Find king
        king_pos = None
        for rr in range(8):
            for cc in range(8):
                p = self.board[rr][cc]
                if p and p[0] == 'k' and p[1] == color:
                    king_pos = (rr, cc)
                    break
            if king_pos:
                break

        # Handle en passant capture
        en_passant_captured = None
        if piece and piece[0] == 'p' and self.en_passant_target:
            if self.tuple_to_pos(nr, nc) == self.en_passant_target:
                ep_r, ep_c = nr - (1 if color == 'w' else -1), nc
                en_passant_captured = self.board[ep_r][ep_c]
                self.board[ep_r][ep_c] = None

        in_check = False
        if king_pos:
            if self._is_square_attacked(king_pos[0], king_pos[1], 'b' if color == 'w' else 'w'):
                in_check = True

        # Undo
        self.board[r][c] = piece
        self.board[nr][nc] = captured
        if en_passant_captured:
            ep_r, ep_c = nr - (1 if color == 'w' else -1), nc
            self.board[ep_r][ep_c] = en_passant_captured

        return in_check

    def is_in_check(self, color):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p[0] == 'k' and p[1] == color:
                    return self._is_square_attacked(r, c, 'b' if color == 'w' else 'w')
        return False

    def is_checkmate(self, color):
        if not self.is_in_check(color):
            return False
        return len(self.get_all_moves(color)) == 0

    def is_stalemate(self, color):
        if self.is_in_check(color):
            return False
        return len(self.get_all_moves(color)) == 0

    def move(self, from_pos, to_pos, promotion='q'):
        fr, fc = self.pos_to_tuple(from_pos)
        tr, tc = self.pos_to_tuple(to_pos)
        piece = self.board[fr][fc]

        if not piece:
            return False, "No piece at source"

        if piece[1] != self.turn:
            return False, f"It's {'White' if self.turn == 'w' else 'Black'}'s turn"

        legal_moves = self.get_piece_moves(fr, fc, piece)
        if (tr, tc) not in legal_moves:
            return False, "Illegal move"

        # En passant capture
        captured_square = None
        if piece[0] == 'p' and self.en_passant_target == to_pos:
            captured_square = (fr, tc)
            captured_piece = self.board[captured_square[0]][captured_square[1]]
        else:
            captured_piece = self.board[tr][tc]

        # Execute move
        self.board[tr][tc] = piece
        self.board[fr][fc] = None

        # Clear en passant
        self.en_passant_target = None

        # Set en passant target for double pawn push
        if piece[0] == 'p' and abs(tr - fr) == 2:
            self.en_passant_target = self.tuple_to_pos((fr + tr) // 2, fc)

        # Pawn promotion
        if piece[0] == 'p' and (tr == 0 or tr == 7):
            self.board[tr][tc] = promotion + piece[1]

        # Castling
        if piece[0] == 'k':
            if tc - fc == 2:  # Kingside
                self.board[tr][5] = self.board[tr][7]
                self.board[tr][7] = None
            elif tc - fc == -2:  # Queenside
                self.board[tr][3] = self.board[tr][0]
                self.board[tr][0] = None
            if piece[1] == 'w':
                self.castling_rights['K'] = False
                self.castling_rights['Q'] = False
            else:
                self.castling_rights['k'] = False
                self.castling_rights['q'] = False

        # Rook moved flag
        if piece[0] == 'r':
            if piece[1] == 'w':
                if fr == 7 and fc == 0:
                    self.castling_rights['Q'] = False
                elif fr == 7 and fc == 7:
                    self.castling_rights['K'] = False
            else:
                if fr == 0 and fc == 0:
                    self.castling_rights['q'] = False
                elif fr == 0 and fc == 7:
                    self.castling_rights['k'] = False

        # En passant actual capture
        if captured_square:
            self.board[captured_square[0]][captured_square[1]] = None

        self.move_history.append((from_pos, to_pos, piece))
        self.turn = 'b' if self.turn == 'w' else 'w'

        # Check for checkmate/stalemate
        opp = self.turn
        if self.is_checkmate(opp):
            return True, "Checkmate!"
        elif self.is_stalemate(opp):
            return True, "Stalemate!"
        elif self.is_in_check(opp):
            return True, "Check!"

        return True, "OK"

    def parse_move(self, move_str):
        parts = move_str.strip().split()
        if len(parts) >= 2:
            return parts[0].lower(), parts[1].lower()
        return None, None


def main():
    board = ChessBoard()
    print("=== Chess Game ===")
    print("Enter moves as: e2 e4")
    print("Special: 'undo', 'exit', 'moves' for available moves")
    print()

    while True:
        board.display()
        turn_name = "White" if board.turn == 'w' else "Black"
        print(f"\n{turn_name}'s turn")

        # Show check status
        if board.is_in_check(board.turn):
            print("⚠ You are in CHECK!")

        cmd = input("> ").strip().lower()

        if cmd == 'exit':
            print("Game ended.")
            break
        elif cmd == 'undo':
            if len(board.move_history) >= 2:
                for _ in range(2):
                    if board.move_history:
                        last = board.move_history.pop()
                        fr, fc = board.pos_to_tuple(last[0])
                        tr, tc = board.pos_to_tuple(last[1])
                        piece = last[2]
                        board.board[fr][fc] = piece
                        board.board[tr][tc] = None
                board.turn = 'w'
                print("Last two moves undone.")
            elif len(board.move_history) == 1:
                last = board.move_history.pop()
                fr, fc = board.pos_to_tuple(last[0])
                tr, tc = board.pos_to_tuple(last[1])
                piece = last[2]
                board.board[fr][fc] = piece
                board.board[tr][tc] = None
                board.turn = 'w'
                print("Move undone.")
            else:
                print("No moves to undo.")
            continue
        elif cmd == 'moves':
            moves = board.get_all_moves(board.turn)
            if moves:
                move_list = [board.tuple_to_pos(m[0], m[1]) for m in moves]
                print(f"Available moves: {', '.join(move_list)}")
            else:
                print("No legal moves available.")
            continue

        from_pos, to_pos = board.parse_move(cmd)
        if not from_pos or not to_pos:
            print("Invalid format. Use: e2 e4")
            continue

        if len(from_pos) != 2 or len(to_pos) != 2:
            print("Invalid positions.")
            continue

        # Try promotion
        promotion = 'q'
        if len(cmd.split()) >= 3:
            promotion = cmd.split()[2].lower()

        success, message = board.move(from_pos, to_pos, promotion)
        if success:
            print(f"✓ {message}")
            if message in ["Checkmate!", "Stalemate!"]:
                board.display()
                print("Game over!")
                break
        else:
            print(f"✗ {message}")


if __name__ == "__main__":
    main()