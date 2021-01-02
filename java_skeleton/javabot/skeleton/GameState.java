package javabot.skeleton;

/**
 * Stores higher state information across many rounds of poker.
 */
public class GameState {
    public final int bankroll;
    public final int oppBankroll;
    public final float gameClock;
    public final int roundNum;

    public GameState(int bankroll, int oppBankroll, float gameClock, int roundNum) {
        this.bankroll = bankroll;
        this.oppBankroll = oppBankroll;
        this.gameClock = gameClock;
        this.roundNum = roundNum;
    }
}